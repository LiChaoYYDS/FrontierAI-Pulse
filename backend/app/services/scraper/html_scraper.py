"""
通用网页抓取器（HtmlScraper）

本次优化：
  1. 新增详情页递归抓取：列表页命中文章后，并发跟进各自的详情页获取完整正文
     - Semaphore 控制并发度（默认 3），避免瞬间发起大量请求被封禁
     - 详情页失败不影响整批：异常在每个请求内部静默处理
  2. 新增自动选择器检测 auto_detect_selector()：
     - 按优先级尝试常见文章容器 CSS 选择器，返回命中有效块最多的那个
     - 覆盖绝大多数技术博客结构，无需用户手动填写 CSS 选择器
"""
import asyncio
import logging

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .base import BaseScraper, RawArticle

logger = logging.getLogger("uvicorn")

# 模拟浏览器头，降低被封风险
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 自动检测时按优先级尝试的文章容器选择器
# 顺序即优先级：语义标签优先，通用 class 模式次之
_ARTICLE_CANDIDATES = [
    "article",
    "[class*='post']",
    "[class*='article']",
    "[class*='entry']",
    "[class*='card']",
    "li[class*='item']",
    ".blog-post",
    ".news-item",
    "[class*='content']",
]

# 详情页正文优先候选容器（语义从强到弱）
_DETAIL_BODY_CANDIDATES = ["article", "main", ".content", ".post-content", "#content", "body"]

# 列表页内容截断长度（引言/摘要）
_LIST_CONTENT_LIMIT = 500
# 详情页正文截断长度
_DETAIL_CONTENT_LIMIT = 8000


def auto_detect_selector(soup: BeautifulSoup) -> str | None:
    """
    启发式自动检测列表页的文章容器 CSS 选择器。

    策略：按 _ARTICLE_CANDIDATES 优先级逐一尝试，
    统计有效块数量（正文 > 30 字符），返回命中最多的选择器。
    命中数 < 2 则认为无法自动检测，返回 None。

    Args:
        soup: 已解析的列表页 BeautifulSoup 对象

    Returns:
        命中最多有效文章块的 CSS 选择器，或 None（检测失败）
    """
    best_selector, best_count = None, 0

    for sel in _ARTICLE_CANDIDATES:
        try:
            blocks = soup.select(sel)
            # 过滤掉文本太短的块（导航栏、侧边栏等噪音）
            valid = [b for b in blocks if len(b.get_text(strip=True)) > 30]
            if len(valid) > best_count:
                best_count = len(valid)
                best_selector = sel
        except Exception:
            continue  # 非法选择器跳过

    result = best_selector if best_count >= 2 else None
    logger.debug("[HtmlScraper] 自动检测选择器：%s（命中 %d 个有效块）", result, best_count)
    return result


async def _fetch_detail(
    client: httpx.AsyncClient,
    url: str,
    delay_seconds: float,
    semaphore: asyncio.Semaphore,
) -> str:
    """
    抓取单篇文章详情页的正文内容。

    使用 semaphore 控制并发数，使用 delay_seconds 控制请求间隔，
    任何异常（网络超时、解析失败等）都静默返回空字符串，
    确保一篇详情页失败不中断整个列表的处理。

    Args:
        client        : 复用调用方的 httpx 客户端（共享连接池）
        url           : 详情页 URL
        delay_seconds : 请求前等待时间，避免频率过高被封
        semaphore     : 并发控制信号量

    Returns:
        正文文本（最多 _DETAIL_CONTENT_LIMIT 字符），失败时返回 ""
    """
    async with semaphore:
        try:
            if delay_seconds:
                await asyncio.sleep(delay_seconds)

            resp = await client.get(url, timeout=20)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # 按优先级尝试正文容器
            body_el = None
            for sel in _DETAIL_BODY_CANDIDATES:
                body_el = soup.select_one(sel)
                if body_el and len(body_el.get_text(strip=True)) > 100:
                    break

            if not body_el:
                return ""

            text = body_el.get_text(separator="\n", strip=True)
            return text[:_DETAIL_CONTENT_LIMIT]

        except Exception as e:
            logger.debug("[HtmlScraper] 详情页抓取失败 %s: %s", url, e)
            return ""  # 失败静默处理，不影响整批


class HtmlScraper(BaseScraper):
    """
    通用网页抓取器。

    支持两种工作模式：
      1. 仅列表页（fetch_detail=False，默认兼容旧行为）：
         从列表页抠出标题 + 链接 + 摘要片段（_LIST_CONTENT_LIMIT 字符）
      2. 列表页 + 详情页（fetch_detail=True）：
         先抓列表页获取 URL 列表，再并发跟进各详情页获取完整正文

    CSS 选择器支持自动检测：
      article_selector=None 时自动调用 auto_detect_selector()，
      检测失败则退化到返回空列表并记录警告日志。
    """

    def __init__(
        self,
        source_id: int,
        source_url: str,
        article_selector: str | None = "article",
        title_selector: str = "h1, h2",
        link_selector: str = "a",
        delay_seconds: float = 0,
        fetch_detail: bool = False,
        detail_concurrency: int = 3,
        extra_headers: dict | None = None,
    ):
        """
        Args:
            source_id         : 来源 ID（由调度器注入）
            source_url        : 列表页 URL
            article_selector  : 文章容器 CSS 选择器；None 表示自动检测
            title_selector    : 标题元素选择器（在文章容器内部查找）
            link_selector     : 链接元素选择器（在文章容器内部查找）
            delay_seconds     : 每次请求前的等待秒数，控制抓取频率
            fetch_detail      : True 时递归抓取详情页正文
            detail_concurrency: 详情页并发抓取数（Semaphore 上限）
            extra_headers     : 额外请求头（覆盖默认 _HEADERS）
        """
        super().__init__(source_id, source_url)
        self.article_selector = article_selector
        self.title_selector = title_selector
        self.link_selector = link_selector
        self.delay_seconds = delay_seconds
        self.fetch_detail = fetch_detail
        self.detail_concurrency = detail_concurrency
        self.headers = {**_HEADERS, **(extra_headers or {})}

    async def fetch(self) -> list[RawArticle]:
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)

        async with httpx.AsyncClient(
            headers=self.headers,
            follow_redirects=True,
        ) as client:
            # ── 第一步：抓取列表页 ───────────────────────────────────────────────
            resp = await client.get(self.source_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # ── 第二步：确定文章容器选择器 ─────────────────────────────────────────
            selector = self.article_selector
            if selector is None:
                # 用户未指定选择器，尝试自动检测
                selector = auto_detect_selector(soup)
                if selector is None:
                    logger.warning(
                        "[HtmlScraper] source_id=%d 自动选择器检测失败，"
                        "请在 extra_config 中手动指定 article_selector",
                        self.source_id,
                    )
                    return []
                logger.info(
                    "[HtmlScraper] source_id=%d 自动检测到选择器：%s",
                    self.source_id, selector,
                )

            # ── 第三步：解析文章列表 ───────────────────────────────────────────────
            articles: list[RawArticle] = []
            base_domain = urlparse(self.source_url).netloc  # 用于同域过滤

            for block in soup.select(selector):
                title_el = block.select_one(self.title_selector)
                link_el = block.select_one(self.link_selector)

                if not (title_el and link_el):
                    continue

                href = link_el.get("href", "")
                if not href:
                    continue

                # 相对路径转绝对路径
                if not href.startswith("http"):
                    href = urljoin(self.source_url, href)

                # 只跟进同域链接，防止爬虫跑偏到外站，即避免点击的不是当前文章的详情链接
                if urlparse(href).netloc != base_domain:
                    logger.debug("[HtmlScraper] 跳过跨域链接: %s", href)
                    continue

                articles.append(RawArticle(
                    title=title_el.get_text(strip=True),
                    url=href,
                    # 列表页只保留短摘要；fetch_detail=True 时会被详情页内容覆盖
                    content=block.get_text(separator=" ", strip=True)[:_LIST_CONTENT_LIMIT],
                ))

            if not articles:
                logger.warning(
                    "[HtmlScraper] source_id=%d 选择器 '%s' 未命中任何文章块",
                    self.source_id, selector,
                )
                return []

            # ── 第四步（可选）：并发抓取详情页 ────────────────────────────────────
            if self.fetch_detail:
                logger.info(
                    "[HtmlScraper] source_id=%d 开始抓取 %d 篇详情页（并发=%d）",
                    self.source_id, len(articles), self.detail_concurrency,
                )
                semaphore = asyncio.Semaphore(self.detail_concurrency)

                detail_contents = await asyncio.gather(*[
                    _fetch_detail(client, a.url, self.delay_seconds, semaphore)
                    for a in articles
                ])

                # 详情页有内容才覆盖列表页摘要，否则保留原有摘要
                replaced = 0
                for article, detail in zip(articles, detail_contents):
                    if detail:
                        article.content = detail
                        replaced += 1

                logger.info(
                    "[HtmlScraper] source_id=%d 详情页完成：%d/%d 篇成功获取正文",
                    self.source_id, replaced, len(articles),
                )

        return articles
