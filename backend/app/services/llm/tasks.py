"""
AI 文章处理任务模块

改动要点（本次优化）：
  1. 步骤3+4（评分 + 洞察）真正并行化：用 asyncio.gather 同时执行
  2. calculate_score 改为异步（依赖语义相似度，需调用 embedder）
  3. batch_process 从串行改为分批并发（每批 5 篇，避免限流）
"""
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import async_session
from app.models.article import Article
from app.services.llm import summarizer, tagger, insight
from app.services.llm.scorer import calculate_score

logger = logging.getLogger("uvicorn")

# 批量处理时的并发批次大小，平衡效率与限流风险
_BATCH_CONCURRENCY = 5


async def process_article(article_id: int, user_interests: list[str] | None = None) -> None:
    """
    AI 处理单篇文章：摘要 → 标签 → 评分 → 洞察，更新数据库。

    执行策略：
      - 幂等：status 已是 done 则跳过
      - 步骤1+2：摘要和标签并行生成（asyncio.gather）
      - 步骤3+4：评分和洞察并行生成（asyncio.gather + return_exceptions）
      - 任一步骤失败不影响其他步骤，最终标记 process_status=failed

    Args:
        article_id: 文章 ID
        user_interests: 用户兴趣短语列表，用于评分和洞察生成
    """
    async with async_session() as db:
        article = await db.get(Article, article_id)
        if not article:
            logger.warning("[Tasks] article_id=%d 不存在", article_id)
            return
        if article.process_status == "done":
            logger.info("[Tasks] article_id=%d 已处理，跳过", article_id)
            return

        # 标记处理中，防止重复调度
        article.process_status = "processing"
        await db.commit()

        try:
            content = article.content or article.title or ""

            # ── 步骤1+2: 摘要和标签并行生成 ──────────────────────────────────────
            logger.info("[Tasks] article_id=%d 开始处理：步骤1+2（摘要+标签）", article_id)
            summary_text, tags = await asyncio.gather(
                summarizer.summarize(content),
                tagger.extract_tags(content, article.title or ""),
            )
            logger.info(
                "[Tasks] article_id=%d 步骤1+2完成 tags=%s",
                article_id, tags,
            )

            # ── 步骤3+4: 评分和洞察并行（return_exceptions 隔离错误）───────────────
            # 注意：calculate_score 现在是异步函数，与 generate_insight 真正并行
            logger.info("[Tasks] article_id=%d 开始步骤3+4（评分+洞察）并行执行", article_id)
            interests = user_interests or []

            score_result, insight_result = await asyncio.gather(
                calculate_score(article.embedding, interests),
                insight.generate_insight(
                    article.title or "", summary_text, tags, interests
                ),
                return_exceptions=True,  # 关键：单个失败不中断整体
            )

            # 处理评分结果（可能是异常）
            if isinstance(score_result, Exception):
                logger.error(
                    "[Tasks] article_id=%d 评分失败，使用兜底值50: %s",
                    article_id, score_result,
                )
                score = 50
            else:
                score = score_result

            # 处理洞察结果（可能是异常）
            if isinstance(insight_result, Exception):
                logger.error(
                    "[Tasks] article_id=%d 洞察生成失败: %s",
                    article_id, insight_result,
                )
                insight_text = None
            else:
                insight_text = insight_result if insight_result else None

            logger.info(
                "[Tasks] article_id=%d 步骤3+4完成 score=%d insight=%s",
                article_id, score, "有" if insight_text else "无",
            )

            # ── 写回数据库 ─────────────────────────────────────────────────────
            article.summary = summary_text
            article.tags = tags
            article.importance_score = score
            article.insight = insight_text
            article.process_status = "done"

            logger.info("[Tasks] article_id=%d 处理完成并写库", article_id)

        except Exception as e:
            logger.error("[Tasks] article_id=%d 处理失败（顶层异常）: %s", article_id, e, exc_info=True)
            article.process_status = "failed"

        await db.commit()


async def batch_process(article_ids: list[int], user_interests: list[str] | None = None) -> dict:
    """
    批量处理多篇文章，返回成功/失败统计。

    改动要点（本次优化）：
      - 从串行 for 循环改为分批并发（每批 _BATCH_CONCURRENCY 篇）
      - 每批内部用 asyncio.gather 并行执行，批与批之间顺序执行
      - 避免一次性发起大量 LLM 请求触发限流，平衡吞吐量与稳定性

    Args:
        article_ids: 待处理文章 ID 列表
        user_interests: 用户兴趣短语列表

    Returns:
        {"success": int, "failed": int, "skipped": int}
    """
    results = {"success": 0, "failed": 0, "skipped": 0}
    total = len(article_ids)

    logger.info(
        "[Tasks] 批量处理开始：共 %d 篇文章，每批并发 %d 篇",
        total, _BATCH_CONCURRENCY,
    )

    # 分批并发：每批最多 _BATCH_CONCURRENCY 篇
    """
    range:从0开始，步长为_BATCH_CONCURRENCY,总数total,即每次增长_BATCH_CONCURRENCY，直到total
    enumerate:以每次的步长为循环，如一开始range得到0，enumerate(0,start=1)=>batch_idx=1,i=0，第二轮range得到5，enumerate(5,start=1)=>batch_idx=1,i=5
    由此可以得出，batch_idx是代表的批次，i代表的是取的文章数，多少篇
    """
    for batch_idx, i in enumerate(range(0, total, _BATCH_CONCURRENCY), start=1):
        chunk = article_ids[i : i + _BATCH_CONCURRENCY]
        logger.info(
            "[Tasks] 批次 %d/%d 开始：文章 ID %s",
            batch_idx, (total + _BATCH_CONCURRENCY - 1) // _BATCH_CONCURRENCY, chunk,
        )

        # 批内并行执行，return_exceptions=True 确保单个失败不影响其他
        batch_results = await asyncio.gather(
            *[process_article(aid, user_interests) for aid in chunk],
            return_exceptions=True,
        )

        # 统计本批次结果
        for aid, result in zip(chunk, batch_results):
            if isinstance(result, Exception):
                logger.error("[Tasks] article_id=%d 处理异常: %s", aid, result)
                results["failed"] += 1
            else:
                results["success"] += 1

        logger.info(
            "[Tasks] 批次 %d/%d 完成：成功 %d 失败 %d",
            batch_idx, (total + _BATCH_CONCURRENCY - 1) // _BATCH_CONCURRENCY,
            results["success"], results["failed"],
        )

    logger.info(
        "[Tasks] 批量处理完成：总计 %d 篇，成功 %d 失败 %d",
        total, results["success"], results["failed"],
    )
    return results
