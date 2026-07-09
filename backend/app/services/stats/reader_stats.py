"""
仪表盘统计服务

提供六个模块所需的数据库聚合查询，全部并行执行。
每个子函数独立创建 session，避免同一 AsyncSession 并发操作报错。
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from app.db.config import async_session
from app.schemas.dashboard import (
    AIAccuracy,
    DailyCount,
    DashboardData,
    OverviewStats,
    ReadFunnel,
    SourceContribution,
    TagCount,
)
from app.models.article import Article
from app.models.source import Source


# ── 各模块查询（每个函数独立 session）────────────────────────────────────────────

async def _get_overview() -> OverviewStats:
    since_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    async with async_session() as db:
        total         = (await db.execute(select(func.count(Article.id)))).scalar() or 0
        today_new     = (await db.execute(select(func.count(Article.id)).where(Article.created_at >= since_today))).scalar() or 0
        read_count    = (await db.execute(select(func.count(Article.id)).where(Article.is_read == True))).scalar() or 0
        fav_count     = (await db.execute(select(func.count(Article.id)).where(Article.is_favorite == True))).scalar() or 0
        active_src    = (await db.execute(select(func.count(Source.id)).where(Source.is_active == True))).scalar() or 0
        kn_nodes      = (await db.execute(text("SELECT COUNT(*) FROM knowledge_nodes"))).scalar() or 0
        unique_tags   = (await db.execute(text(
            "SELECT COUNT(DISTINCT tag) FROM "
            "(SELECT unnest(tags) AS tag FROM articles WHERE tags IS NOT NULL) t"
        ))).scalar() or 0
    return OverviewStats(
        total_articles=total,
        today_new=today_new,
        read_count=read_count,
        favorite_count=fav_count,
        total_sources=active_src,
        total_knowledge_nodes=kn_nodes,
        total_unique_tags=unique_tags,
    )


async def _get_growth_trend(days: int) -> list[DailyCount]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT TO_CHAR(created_at AT TIME ZONE 'UTC', 'MM-DD') AS day, COUNT(*) AS cnt
            FROM articles
            WHERE created_at >= :since
            GROUP BY day
            ORDER BY day
        """), {"since": since})
        return [DailyCount(date=row[0], count=row[1]) for row in result.all()]


async def _get_funnel() -> ReadFunnel:
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT
                COUNT(*)                                          AS total,
                COUNT(*) FILTER (WHERE process_status = 'done')  AS ai_processed,
                COUNT(*) FILTER (WHERE is_read = TRUE)           AS user_read,
                COUNT(*) FILTER (WHERE is_favorite = TRUE)       AS user_favorite,
                COUNT(*) FILTER (WHERE insight IS NOT NULL)      AS has_insight
            FROM articles
        """))
        row = result.one()
    return ReadFunnel(
        total_articles=row[0] or 0,
        ai_processed=row[1]   or 0,
        user_read=row[2]       or 0,
        user_favorite=row[3]   or 0,
        has_insight=row[4]     or 0,
    )


async def _get_ai_accuracy() -> AIAccuracy:
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE importance_score >= 80)                    AS hs_total,
                COUNT(*) FILTER (WHERE importance_score >= 80 AND is_read = TRUE) AS hs_read,
                COUNT(*) FILTER (WHERE is_read = TRUE)                            AS read_total,
                COUNT(*) FILTER (WHERE is_read = TRUE AND importance_score >= 80) AS read_hs
            FROM articles
        """))
        row = result.one()
    hs_total, hs_read, read_total, read_hs = (row[i] or 0 for i in range(4))
    return AIAccuracy(
        high_score_total=hs_total,
        high_score_read=hs_read,
        read_rate=round(hs_read / hs_total * 100, 1) if hs_total else 0.0,
        read_total=read_total,
        read_high_score=read_hs,
        quality_rate=round(read_hs / read_total * 100, 1) if read_total else 0.0,
    )


async def _get_top_sources() -> list[SourceContribution]:
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT a.source_id, s.name, COUNT(*) AS cnt,
                   ROUND(AVG(a.importance_score)::numeric, 1) AS avg_score
            FROM articles a
            JOIN sources s ON s.id = a.source_id
            WHERE a.source_id IS NOT NULL
            GROUP BY a.source_id, s.name
            ORDER BY cnt DESC
            LIMIT 10
        """))
        return [
            SourceContribution(
                source_id=row[0], source_name=row[1],
                article_count=row[2], avg_score=float(row[3] or 0),
            )
            for row in result.all()
        ]


async def _get_tag_distribution() -> list[TagCount]:
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT tag, COUNT(*) AS cnt
            FROM (SELECT unnest(tags) AS tag FROM articles WHERE tags IS NOT NULL) t
            GROUP BY tag ORDER BY cnt DESC LIMIT 10
        """))
        return [TagCount(tag=row[0], count=row[1]) for row in result.all()]


# ── 主入口（无需外部 session，子函数各自管理）────────────────────────────────────

async def get_dashboard_data(days: int = 30) -> DashboardData:
    """
    并行执行全部六个模块的数据库查询，返回完整仪表盘数据。
    days: 内容增长趋势的时间窗口（7 / 30 / 90），默认30天。
    """
    overview, growth, funnel, accuracy, sources, tags = await asyncio.gather(
        _get_overview(),
        _get_growth_trend(days),
        _get_funnel(),
        _get_ai_accuracy(),
        _get_top_sources(),
        _get_tag_distribution(),
    )
    return DashboardData(
        overview=overview,
        growth_trend=growth,
        funnel=funnel,
        ai_accuracy=accuracy,
        top_sources=sources,
        tag_distribution=tags,
    )
