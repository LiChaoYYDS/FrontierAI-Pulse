"""
周报生成服务（结构化版本）

架构：
  - DB 查询全部并行执行（asyncio.gather）
  - 仅 1 次 LLM 调用，生成热点趋势描述 + 行动建议 + 下周关注
  - 三级降级策略确保精选文章永不为空

层职责：
  - 本模块：纯业务逻辑，不直接依赖 FastAPI
  - schemas/report.py：数据契约
  - provider_factory：LLM 访问
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.schemas.report import (
    ActionItem,
    ArticleItem,
    DailyCount,
    InsightItem,
    TagCount,
    TrendItem,
    WeeklyOverview,
    WeeklyReportData,
)
from app.services.llm.provider_factory import get_provider

logger = logging.getLogger("uvicorn")

# 估算阅读时长：中文约300字/分钟，英文约200词/分钟，取300字通用
_CHARS_PER_MINUTE = 300


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _read_minutes(article: Article) -> int:
    """根据正文或摘要估算阅读时长（分钟），最少1分钟。"""
    text_len = len(article.content or article.summary or article.title or "")
    return max(1, round(text_len / _CHARS_PER_MINUTE))


def _period_str(since: datetime) -> str:
    now = datetime.now()
    return f"{since.strftime('%Y年%m月%d日')} — {now.strftime('%m月%d日')}"


def _trend_direction(change: int) -> str:
    if change >= 5:
        return "up_strong"
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "stable"


# ── DB 查询层（纯数据，无 LLM）────────────────────────────────────────────────

async def _build_overview(db: AsyncSession, since: datetime) -> WeeklyOverview:
    """统计本周概览指标。"""
    total_res = await db.execute(
        select(func.count(Article.id)).where(Article.created_at >= since)
    )
    total = total_res.scalar_one()

    read_res = await db.execute(
        select(func.count(Article.id))
        .where(Article.created_at >= since, Article.is_read == True)
    )
    read_count = read_res.scalar_one()

    # 取已读文章估算阅读时长
    read_articles_res = await db.execute(
        select(Article).where(Article.created_at >= since, Article.is_read == True)
    )
    read_articles = read_articles_res.scalars().all()
    read_minutes = sum(_read_minutes(a) for a in read_articles)

    # 本周出现的不重复标签数作为"知识点数"
    tags_res = await db.execute(
        text("""
            SELECT COUNT(DISTINCT tag)
            FROM (
                SELECT unnest(tags) AS tag
                FROM articles
                WHERE created_at >= :since AND tags IS NOT NULL
            ) t
        """),
        {"since": since},
    )
    knowledge_points = tags_res.scalar_one() or 0

    return WeeklyOverview(
        total_articles=total,
        read_count=read_count,
        read_minutes=read_minutes,
        knowledge_points=knowledge_points,
    )


async def _build_tag_stats(
    db: AsyncSession, since: datetime, prev_since: datetime
) -> tuple[list[tuple[str, int]], dict[str, int]]:
    """
    返回 (本周 top 标签列表, 上周标签计数字典)，供后续计算趋势。
    """
    this_week_res = await db.execute(
        text("""
            SELECT tag, COUNT(*) AS cnt
            FROM (SELECT unnest(tags) AS tag FROM articles
                  WHERE created_at >= :since AND tags IS NOT NULL) t
            GROUP BY tag
            ORDER BY cnt DESC
            LIMIT 10
        """),
        {"since": since},
    )
    this_week = [(row[0], row[1]) for row in this_week_res.all()]

    last_week_res = await db.execute(
        text("""
            SELECT tag, COUNT(*) AS cnt
            FROM (SELECT unnest(tags) AS tag FROM articles
                  WHERE created_at >= :prev AND created_at < :since
                  AND tags IS NOT NULL) t
            GROUP BY tag
        """),
        {"prev": prev_since, "since": since},
    )
    last_week = {row[0]: row[1] for row in last_week_res.all()}

    return this_week, last_week


async def _build_curated_articles(
    db: AsyncSession, since: datetime, user_interests: list[str]
) -> list[ArticleItem]:
    """
    三级降级策略保证至少返回 5 篇精选文章：
      第一级：本周 + 有摘要 + 高分
      第二级：近30天 + 有摘要 + 高分
      第三级：全库最高分（兜底）
    """
    async def _query(time_filter, limit=8):
        stmt = (
            select(Article)
            .where(time_filter, Article.summary.isnot(None))
            .order_by(Article.importance_score.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    articles = await _query(Article.created_at >= since)

    if len(articles) < 5:
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        articles = await _query(Article.created_at >= month_ago)

    if len(articles) < 5:
        stmt = (
            select(Article)
            .where(Article.summary.isnot(None))
            .order_by(Article.importance_score.desc())
            .limit(8)
        )
        articles = (await db.execute(stmt)).scalars().all()

    return [
        ArticleItem(
            id=a.id,
            title=a.title or "",
            url=a.url or "",
            summary=a.summary or "",
            tags=a.tags or [],
            score=a.importance_score or 50,
            read_minutes=_read_minutes(a),
        )
        for a in articles[:8]
    ]


async def _build_insights(db: AsyncSession, since: datetime) -> list[InsightItem]:
    """取本周有 AI 洞察的文章，兜底扩展到近30天。"""
    stmt = (
        select(Article)
        .where(Article.created_at >= since, Article.insight.isnot(None))
        .order_by(Article.importance_score.desc())
        .limit(5)
    )
    articles = (await db.execute(stmt)).scalars().all()

    if not articles:
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = (
            select(Article)
            .where(Article.created_at >= month_ago, Article.insight.isnot(None))
            .order_by(Article.importance_score.desc())
            .limit(5)
        )
        articles = (await db.execute(stmt)).scalars().all()

    return [
        InsightItem(title=a.title or "", url=a.url or "", insight=a.insight or "")
        for a in articles
    ]


async def _build_daily_reads(db: AsyncSession, since: datetime) -> list[DailyCount]:
    """统计最近7天每天新增文章数。"""
    result = await db.execute(
        text("""
            SELECT TO_CHAR(created_at AT TIME ZONE 'UTC', 'MM-DD') AS day,
                   COUNT(*) AS cnt
            FROM articles
            WHERE created_at >= :since
            GROUP BY day
            ORDER BY day
        """),
        {"since": since},
    )
    return [DailyCount(date=row[0], count=row[1]) for row in result.all()]


async def _build_tag_distribution(
    db: AsyncSession, since: datetime
) -> list[TagCount]:
    """统计本周各标签出现次数（前10）。"""
    result = await db.execute(
        text("""
            SELECT tag, COUNT(*) AS cnt
            FROM (SELECT unnest(tags) AS tag FROM articles
                  WHERE created_at >= :since AND tags IS NOT NULL) t
            GROUP BY tag
            ORDER BY cnt DESC
            LIMIT 10
        """),
        {"since": since},
    )
    return [TagCount(tag=row[0], count=row[1]) for row in result.all()]


# ── LLM 调用层（单次调用，JSON输出）──────────────────────────────────────────

async def _build_ai_content(
    top_tags: list[tuple[str, int]],
    last_week_tags: dict[str, int],
    curated: list[ArticleItem],
    user_interests: list[str],
    read_count: int,
) -> tuple[list[TrendItem], list[ActionItem], list[str]]:
    """
    单次 LLM 调用，同时生成：
      - 热点趋势描述（每条一句话）
      - 个性化行动建议（3条）
      - 下周关注方向（3条）

    返回 (trends, actions, next_focus)
    """
    interests_str = "、".join(user_interests[:6]) if user_interests else "技术通用"
    tags_info = "\n".join(
        f"- {tag}：本周{cnt}篇，上周{last_week_tags.get(tag, 0)}篇"
        for tag, cnt in top_tags[:5]
    )
    articles_str = "\n".join(
        f"- 《{a.title}》 标签:{','.join(a.tags[:3])} 匹配度{a.score}%"
        for a in curated[:6]
    )

    prompt = f"""用户兴趣：{interests_str}
本周已读：{read_count} 篇
本周热点标签统计：
{tags_info}
本周精选文章（已有 AI 摘要）：
{articles_str}

请严格按照以下 JSON 格式返回，不要输出任何其他内容：
{{
  "trend_summaries": {{
    "<标签名>": "<一句话趋势描述，15-30字>"
  }},
  "action_items": [
    {{
      "title": "<行动项标题，10字以内>",
      "detail": "<具体步骤，包含工具/框架名称>",
      "time_estimate": "<预估时间，如2小时>",
      "reference_url": "<关联文章URL，没有则空字符串>"
    }}
  ],
  "next_week_focus": ["<方向1>", "<方向2>", "<方向3>"]
}}

要求：
- trend_summaries 覆盖上面所有标签
- action_items 恰好 3 条，必须具体可执行，提及工具/框架名
- next_week_focus 恰好 3 条，结合用户兴趣和本周热点"""

    try:
        provider = get_provider()
        result = await provider.complete(
            prompt=prompt,
            system="你是技术学习顾问，请严格按 JSON 格式输出，不加 Markdown 代码块。",
        )
        raw = result.content.strip()
        # 兼容模型在 JSON 外包裹了 ```json ... ``` 的情况
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)
    except Exception as e:
        logger.warning("[WeeklyReport] LLM 调用失败，使用兜底内容: %s", e)
        data = {}

    trend_summaries: dict[str, str] = data.get("trend_summaries", {})
    raw_actions: list[dict] = data.get("action_items", [])
    next_focus: list[str] = data.get("next_week_focus", [])

    # 组装 TrendItem 列表
    trends = [
        TrendItem(
            tag=tag,
            count=cnt,
            change=cnt - last_week_tags.get(tag, 0),
            direction=_trend_direction(cnt - last_week_tags.get(tag, 0)),
            summary=trend_summaries.get(tag, f"本周{tag}领域新增{cnt}篇资讯，持续活跃。"),
        )
        for tag, cnt in top_tags[:5]
    ]

    # 组装 ActionItem 列表（最多3条，兜底默认）
    default_actions = [
        ActionItem(
            title="深度阅读一篇",
            detail=f"从本周精选中选一篇与{interests_str}相关的文章，摘录核心观点",
            time_estimate="1小时",
        ),
        ActionItem(
            title="动手实践",
            detail="选取一个本周出现的新工具/框架，跑通官方 Quick Start",
            time_estimate="2小时",
        ),
        ActionItem(
            title="整理知识笔记",
            detail="将本周阅读的内容整理为一份简短的 Markdown 笔记",
            time_estimate="30分钟",
        ),
    ]
    actions = [
        ActionItem(**a) for a in raw_actions[:3]
    ] if raw_actions else default_actions

    if not next_focus:
        next_focus = [f"深化{interests_str.split('、')[0]}实践",
                      "关注开源社区动态", "探索 AI 工程化最佳实践"]

    return trends, actions, next_focus[:3]


# ── 主入口 ────────────────────────────────────────────────────────────────────

async def generate_weekly_report(
    db: AsyncSession, user_interests: list[str]
) -> WeeklyReportData:
    """
    生成结构化周报数据。

    执行策略：
      - 所有 DB 查询并行（asyncio.gather）
      - 单次 LLM 调用生成热点描述 + 行动建议 + 下周关注
    """
    now_utc = datetime.now(timezone.utc)
    since = now_utc - timedelta(days=7)
    prev_since = now_utc - timedelta(days=14)

    logger.info("[WeeklyReport] 开始生成，时间窗口: %s ~ now", since.date())

    # ── 所有 DB 查询并行 ──────────────────────────────────────────────────────
    (
        overview,
        (top_tags, last_week_tags),
        curated,
        insights,
        daily_reads,
        tag_dist,
    ) = await asyncio.gather(
        _build_overview(db, since),
        _build_tag_stats(db, since, prev_since),
        _build_curated_articles(db, since, user_interests),
        _build_insights(db, since),
        _build_daily_reads(db, since),
        _build_tag_distribution(db, since),
    )

    logger.info(
        "[WeeklyReport] DB 查询完成：%d篇本周文章，%d篇精选，%d条洞见",
        overview.total_articles, len(curated), len(insights),
    )

    # ── 单次 LLM 调用 ─────────────────────────────────────────────────────────
    trends, actions, next_focus = await _build_ai_content(
        top_tags, last_week_tags, curated, user_interests, overview.read_count
    )

    logger.info("[WeeklyReport] 生成完成")

    return WeeklyReportData(
        period=_period_str(since.replace(tzinfo=None)),
        overview=overview,
        top_trends=trends,
        curated_articles=curated,
        insights=insights,
        action_items=actions,
        next_week_focus=next_focus,
        daily_reads=daily_reads,
        tag_distribution=tag_dist,
    )
