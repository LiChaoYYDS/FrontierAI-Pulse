from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawArticle:
    """采集器产出的原始文章，还没入库。

    为什么用 dataclass 而不是 Pydantic？
    - dataclass 更轻量，不需要验证（这些数据来自外部，验证没有意义）
    - 这是内部传输对象，不是 API 的请求/响应体
    - 减少依赖：dataclass 是标准库
    """
    title: str
    url: str
    content: str | None = None
    summary: str | None = None
    author: str | None = None
    published_at: str | None = None
    tags: list[str] | None = None


class BaseScraper(ABC):
    """所有采集器的基类。子类只需实现 fetch()。

    设计要点：
    - source_id 在构造时注入：采集器不负责查数据库，只负责用给定的 source_id 标记产出
    - fetch() 是异步的：抓取是 IO 密集型操作，用 async 避免阻塞
    - 返回 list 而非单个：一个 RSS feed 通常包含 20-50 篇文章
    """

    def __init__(self, source_id: int, source_url: str):
        self.source_id = source_id
        self.source_url = source_url

    @abstractmethod
    async def fetch(self) -> list[RawArticle]:
        """从来源抓取文章列表。子类必须实现。"""
        ...