"""内置优质技术资讯预设来源列表。
每项以 url 作为唯一标识，与 sources 表通过 url 字段关联。
"""
from dataclasses import dataclass, field


@dataclass
class PresetSource:
    key: str          # 唯一标识符
    name: str
    url: str
    type: str         # rss / arxiv / website / github
    description: str
    category: str     # zh / en
    extra_config: dict = field(default_factory=dict)


PRESET_SOURCES: list[PresetSource] = [
    # ── 中文 ──────────────────────────────────────────
    PresetSource("juejin",     "掘金",       "https://juejin.cn/rss",                 "rss",     "掘金技术热文",          "zh"),
    PresetSource("infoq_zh",   "InfoQ 中文", "https://www.infoq.cn/feed",             "rss",     "InfoQ 中文技术资讯",    "zh"),
    PresetSource("36kr",       "36氪",       "https://36kr.com/feed",                 "rss",     "前沿科技与商业资讯",    "zh"),
    PresetSource("oschina",    "OSCHINA",   "https://www.oschina.net/blog/rss",       "rss",     "开源中国技术资讯",      "zh"),
    PresetSource("sspai",      "少数派",     "https://sspai.com/feed",                 "rss",     "效率工具与科技生活",    "zh"),

    # ── 英文 ──────────────────────────────────────────
    PresetSource("hackernews", "Hacker News",     "https://hnrss.org/frontpage",               "rss",   "Hacker News 前页精选",  "en"),
    PresetSource("devto",      "Dev.to",           "https://dev.to/feed",                       "rss",   "Dev.to 开发者文章",     "en"),
    PresetSource("arxiv_ai",   "arXiv AI",         "http://export.arxiv.org/api/query",         "arxiv", "arXiv AI 最新论文",     "en",
                 {"categories": ["cs.AI", "cs.CL", "cs.LG"]}),
    PresetSource("huggingface","HuggingFace Blog", "https://huggingface.co/blog/feed.xml",      "rss",   "HuggingFace 官方博客",  "en"),
    PresetSource("tldr",       "TLDR Newsletter",  "https://tldr.tech/api/rss/tech",            "rss",   "每日科技简报",          "en"),
    PresetSource("github_trend","GitHub Trending", "https://github.com/trending",               "website","GitHub 每日趋势项目",  "en",
                 {"article_selector": "article.Box-row", "title_selector": "h2", "link_selector": "h2 a"}),
]

# 以 key 为索引，方便快速查找
PRESET_MAP: dict[str, PresetSource] = {s.key: s for s in PRESET_SOURCES}
