from datetime import datetime
from email.utils import parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bs4 import BeautifulSoup

from app.models.article import Article
from .base import RawArticle


def _parse_dt(value: str | datetime | None) -> datetime | None:
    """将各种格式的日期字符串统一转为 datetime，失败返回 None。"""
    if value is None or isinstance(value, datetime):
        return value
    for parser in (
        parsedate_to_datetime,                            # RFC 2822: 'Wed, 24 Jun 2026 14:38:32 GMT'
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),  # ISO 8601
    ):
        try:
            return parser(value)
        except Exception:
            continue
    return None


def _strip_html(raw: str | None) -> str | None:
    if not raw:
        return None
    return BeautifulSoup(raw, "html.parser").get_text(separator=" ", strip=True)


async def save_articles(
    db: AsyncSession,
    raw_articles: list[RawArticle],
    source_id: int,
) -> int:
    """去重 → 清洗 → 批量入库，返回新增数量"""
    if not raw_articles:
        return 0

    urls = [a.url for a in raw_articles if a.url]
    existing = {row[0] for row in (await db.execute(
        select(Article.url).where(Article.url.in_(urls))
    )).all()}
    fresh = [a for a in raw_articles if a.url and a.url not in existing]

    if not fresh:
        return 0

    db.add_all([
        Article(
            title=a.title,
            url=a.url,
            content=_strip_html(a.content),
            summary=a.summary,
            author=a.author,
            published_at=_parse_dt(a.published_at),
            source_id=source_id,
            tags=a.tags or [],
        )
        for a in fresh
    ])
    await db.commit()
    return len(fresh)
