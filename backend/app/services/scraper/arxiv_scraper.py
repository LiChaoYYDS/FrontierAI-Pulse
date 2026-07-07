import xml.etree.ElementTree as ET
import httpx

from .base import BaseScraper, RawArticle


class ArxivScraper(BaseScraper):
    """通过 arXiv API 抓取，支持分类和关键词过滤。

    与 RssScraper 的区别：
    - RSS：固定返回某个分类的最新 N 篇
    - API：可以按关键词/作者/日期精确过滤

    速率限制：连续请求需间隔 ≥5 秒，否则返回 503。
    """

    def __init__(self, source_id: int, source_url: str,
                 categories: list[str] | None = None,
                 keywords: list[str] | None = None):
        super().__init__(source_id, source_url)
        self.categories = categories or ["cs.AI"]
        self.keywords = keywords or []

    async def fetch(self) -> list[RawArticle]:
        # 构造查询：cat:cs.AI+OR+cat:cs.CL ===> +代表空格编码 cat:cs.AI OR cat:cs.CL
        cat_query = "+OR+".join(f"cat:{c}" for c in self.categories)

        # 如果有关键词，追加 AND all:keyword
        keyword_part = ""
        if self.keywords:
            # all:transformer AND all:attention
            kw_query = "+AND+".join(f"all:{kw}" for kw in self.keywords)
            # AND (all:transformer AND all:attention)
            keyword_part = f"+AND+({kw_query})"
        #cat:cs.AI OR cat:cs.CL AND (all:transformer AND all:attention)
        url = (
            f"http://export.arxiv.org/api/query"
            f"?search_query={cat_query}{keyword_part}"
            f"&max_results=30"
            f"&sortBy=submittedDate"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
            # Raise the `HTTPStatusError` if one occurred:如果没获取成功就会抛出一个异常
            resp.raise_for_status()

        return self._parse_atom(resp.text)

    def _parse_atom(self, xml_text: str) -> list[RawArticle]:
        """解析 arXiv API 返回的 Atom XML。

        Atom XML 示例：
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Paper Title</title>
            <id>http://arxiv.org/abs/2606.12345v1</id>
            <summary>Paper abstract...</summary>
            <published>2026-06-23T10:00:00Z</published>
            <author><name>Author Name</name></author>
          </entry>
        </feed>
        """
        #将xml字符串转为Element对象
        root = ET.fromstring(xml_text)
        # 命名空间，每个标签都有一个默认命名空间，所以在获取该标签时需要加上对应的命名空间
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        articles: list[RawArticle] = []
        #findall("atom:entry", ns) 利用 XPath 表达式，在命名空间 ns 的辅助下，找到根节点下所有 <atom:entry> 子元素。每个 <entry> 代表一篇论文。
        for entry in root.findall("atom:entry", ns):
            # 获取论文的标题、链接、摘要、作者、发布时间
            title = entry.findtext("atom:title", "", ns).strip()
            link = entry.findtext("atom:id", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()
            published_at = entry.findtext("atom:published", None, ns)
            # 提取分类标签作为文章的 tags
            category_els = entry.findall("atom:category", ns)
            tags = [c.get("term", "") for c in category_els if c.get("term")]

            articles.append(RawArticle(
                title=title,
                url=link,
                content=summary,
                author=None,
                published_at=published_at,
                tags=tags,  # arXiv 自带分类标签
            ))
        return articles