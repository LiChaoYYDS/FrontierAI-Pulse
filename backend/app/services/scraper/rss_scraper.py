import asyncio
import feedparser

from .base import BaseScraper, RawArticle

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FrontierAI-Pulse/1.0)"}


class RssScraper(BaseScraper):
    """通用 RSS/Atom 采集器（支持 arXiv RSS、HuggingFace Blog 等）"""

    async def fetch(self) -> list[RawArticle]:
        #由于feedparser 是同步的，所以要切换到线程执行，request_headers模拟浏览器 User-Agent，部分 RSS 源会检查请求头，避免被拦截
        feed = await asyncio.to_thread(
            feedparser.parse, self.source_url, request_headers=_HEADERS
        )
        articles: list[RawArticle] = []
        for entry in feed.entries:
            articles.append(RawArticle(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                content=entry.get("summary", ""),
                author=entry.get("author", None),
                published_at=entry.get("published", None),
                tags=[t.term for t in getattr(entry, "tags", [])] or None,
            ))
        return articles
