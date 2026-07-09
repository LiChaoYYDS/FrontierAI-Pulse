from datetime import datetime
from pydantic import BaseModel


class SourceResponse(BaseModel):
    id: int
    name: str
    url: str
    type: str
    description: str | None = None
    is_active: bool
    last_fetched: datetime | None = None

    model_config = {"from_attributes": True}


class CustomSourceCreate(BaseModel):
    """手动添加自定义来源的请求体"""
    name: str
    url: str
    type: str = "rss"             # rss / website / github / arxiv
    description: str | None = None


class SourceActiveUpdate(BaseModel):
    """切换自定义来源启用状态的请求体"""
    is_active: bool
