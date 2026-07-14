"""
抓取调度器

本次优化：
  - fetch_all_active_sources() 从串行 for 循环改为分批并发：
      · asyncio.Semaphore 控制同时在飞的请求数（_FETCH_CONCURRENCY=5）
      · asyncio.wait_for 给每个来源独立超时（_SOURCE_TIMEOUT=60s），
        彻底隔离慢源，不再有队头阻塞问题
      · 任意来源超时或异常，只记录日志，不影响其余来源
"""
import asyncio
import logging

from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.config import async_session
from app.models.source import Source
from .rss_scraper import RssScraper
from .arxiv_scraper import ArxivScraper
from .html_scraper import HtmlScraper
from .pipeline import save_articles

logger = logging.getLogger("uvicorn")
scheduler = AsyncIOScheduler()

# 同时抓取的最大来源数，防止瞬间对所有来源发请求触发限流或打满出口带宽
_FETCH_CONCURRENCY = 5
# 单个来源的最长等待时间（秒），超时后跳过，不阻塞其他来源
_SOURCE_TIMEOUT = 60
# 防止后台 Embedding asyncio.Task 被 GC 回收的强引用集合
_background_embed_tasks: set = set()


def _make_scraper(source: Source):
    """采集器工厂：根据 source.type 和 extra_config 创建对应的 Scraper。"""
    extra = source.extra_config or {}
    if source.type == "arxiv":
        return ArxivScraper(
            source.id, source.url,
            categories=extra.get("categories"),
            keywords=extra.get("keywords"),
        )
    if source.type == "website":
        return HtmlScraper(
            source.id, source.url,
            # article_selector=None 触发自动检测；用户也可在 extra_config 中手动指定
            article_selector=extra.get("article_selector", None),
            title_selector=extra.get("title_selector", "h1, h2"),
            link_selector=extra.get("link_selector", "a"),
            delay_seconds=extra.get("delay_seconds", 1.0),
            # fetch_detail=True 时递归抓取详情页正文，默认关闭（可按来源单独开启）
            fetch_detail=extra.get("fetch_detail", True),
            detail_concurrency=extra.get("detail_concurrency", 3),
        )
    return RssScraper(source.id, source.url)


async def fetch_single_source(source_id: int) -> int:
    """
    抓取单个来源，返回新增文章数。可被 API 端点直接调用。
    有新文章时自动在后台触发 Embedding 生成，不阻塞接口返回。

    Args:
        source_id: 来源 ID

    Returns:
        本次新增文章数
    """
    async with async_session() as db:
        source = await db.get(Source, source_id)
        if not source:
            raise ValueError(f"来源 {source_id} 不存在")

        scraper = _make_scraper(source)
        raw_articles = await scraper.fetch()
        count = await save_articles(db, raw_articles, source.id)

        from sqlalchemy import func
        source.last_fetched = func.now()
        await db.commit()

    logger.info("[Scraper] %s 新增 %d 篇", source.name, count)

    # 有新文章时，后台自动触发 Embedding 生成
    # 局部导入避免循环依赖；任务引用存入集合防止被 GC 回收
    if count > 0:
        from app.services.rag.background_jobs import embed_job, run_embed_job
        if not embed_job["running"]:
            task = asyncio.create_task(run_embed_job())
            _background_embed_tasks.add(task)
            task.add_done_callback(_background_embed_tasks.discard)
            logger.info("[Scraper] 已触发后台 Embedding 任务（%d 篇新文章待向量化）", count)
        else:
            logger.info("[Scraper] Embedding 任务已在运行中，本次新文章将在当前批次处理")

    return count


async def _fetch_with_guard(source: Source, semaphore: asyncio.Semaphore) -> None:
    """
    带并发控制 + 独立超时的单来源抓取。

    · semaphore  限制同时运行的来源数，避免瞬间并发过高
    · wait_for   给每个来源独立超时预算，慢源只占用一个并发槽最多 _SOURCE_TIMEOUT 秒
    · 所有异常（超时、网络错误、解析失败）均在此函数内部处理，
      保证调用方的 gather 永远不会因为单个来源而整体失败

    Args:
        source   : 来源 ORM 对象
        semaphore: 并发控制信号量
    """
    async with semaphore:
        try:
            await asyncio.wait_for(
                fetch_single_source(source.id),
                timeout=_SOURCE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[Scraper] 来源 %d（%s）超时（>%ds），已跳过",
                source.id, source.name, _SOURCE_TIMEOUT,
            )
        except Exception as e:
            logger.warning(
                "[Scraper] 来源 %d（%s）抓取失败: %s",
                source.id, source.name, e,
            )


async def fetch_all_active_sources() -> None:
    """
    定时任务：并发抓取所有活跃来源。

    改动说明（原串行 → 现并发）：
      原实现用 for 循环串行 await，一个慢源会阻塞后续所有来源（队头阻塞）。
      现在用 asyncio.gather + Semaphore 并发抓取：
        - 同时最多 _FETCH_CONCURRENCY 个来源在抓取
        - 每个来源独立超时，互不干扰
        - 全部来源触发后等待所有完成，再结束本次调度周期
    """
    async with async_session() as db:
        result = await db.execute(select(Source).where(Source.is_active == True))
        sources = result.scalars().all()

    if not sources:
        logger.info("[Scraper] 无活跃来源，跳过本次调度")
        return

    logger.info("[Scraper] 本次调度：共 %d 个活跃来源，并发上限 %d", len(sources), _FETCH_CONCURRENCY)
    semaphore = asyncio.Semaphore(_FETCH_CONCURRENCY)

    # 所有来源同时启动，由 semaphore 控制实际并发度
    await asyncio.gather(*[
        _fetch_with_guard(source, semaphore)
        for source in sources
    ])

    logger.info("[Scraper] 本次调度完成，共处理 %d 个来源", len(sources))


def start_scheduler(interval_hours: int = 2) -> None:
    """
    启动定时任务：每 interval_hours 小时抓取一次活跃来源。

    Args:
        interval_hours: 抓取间隔小时数
    """
    scheduler.add_job(
        fetch_all_active_sources,
        trigger="interval",
        hours=interval_hours,
        id="fetch_all_sources",
        max_instances=1,     # 防止上一次未跑完就触发下一次
        misfire_grace_time=60,
        coalesce=True,       # 积压多次触发时只执行一次
    )
    scheduler.start()
    logger.info("[Scraper] 定时调度已启动，每 %d 小时抓取一次", interval_hours)


def stop_scheduler() -> None:
    """停止调度器，等待当前任务自然结束。"""
    scheduler.shutdown(wait=False)
