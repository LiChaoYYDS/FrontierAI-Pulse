from datetime import datetime

from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    content: str | None = None
    summary: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    source_id: int | None = None
    source_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance_score: int = 50
    is_read: bool = False
    is_favorite: bool = False
    is_liked: bool = False
    notes: str | None = None
    insight: str | None = None
    process_status: str | None = "pending"
    created_at: datetime | None = None
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class ArticlePage(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ArticleUpdate(BaseModel):
    """PATCH 请求体：只传需要更新的字段"""
    is_read: bool | None = None
    is_favorite: bool | None = None
    is_liked: bool | None = None
    notes: str | None = None
