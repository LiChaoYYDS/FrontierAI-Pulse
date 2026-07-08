"""
RAG 问答相关的 Pydantic Schema 定义
"""
from pydantic import BaseModel

from app.schemas.article import ArticleResponse


class HistoryItem(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[HistoryItem] = []  # 前端传来的对话历史，最多携带最近6条


class AskResponse(BaseModel):
    answer: str
    layer: str          # personal / curated / general
    layer_desc: str     # 检索层中文描述
    sources: list[ArticleResponse]  # 回答依据的文章列表


class EmbedStatusResponse(BaseModel):
    total: int          # 文章总数
    embedded: int       # 已有向量的文章数
    pending: int        # 待向量化数量
    coverage_pct: float # 覆盖率百分比
    job_running: bool   # 是否有批量任务在跑


class RescoreRequest(BaseModel):
    interests: list[str]  # 用户兴趣短语列表，如 ["大语言模型", "rag", "云原生"]


class RescoreResponse(BaseModel):
    message: str
    status: dict  # 当前任务状态快照
