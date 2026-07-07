from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.source import Source


async def get_summary(db: AsyncSession) -> dict:
    since_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total, today_new, read_count, fav_count, avg_score, active_sources = (
        await db.execute(select(func.count(Article.id)))
    ).scalar() or 0, (
        await db.execute(select(func.count(Article.id)).where(Article.created_at >= since_today))
    ).scalar() or 0, (
        await db.execute(select(func.count(Article.id)).where(Article.is_read == True))
    ).scalar() or 0, (
        await db.execute(select(func.count(Article.id)).where(Article.is_favorite == True))
    ).scalar() or 0, (
        await db.execute(select(func.avg(Article.importance_score)).where(Article.importance_score > 0))
    ).scalar() or 0, (
        await db.execute(select(func.count(Source.id)).where(Source.is_active == True))
    ).scalar() or 0

    return {
        "total_articles": total,
        "today_new": today_new,
        "read_count": read_count,
        "favorite_count": fav_count,
        "avg_score": round(float(avg_score), 1),
        "active_sources": active_sources,
    }
