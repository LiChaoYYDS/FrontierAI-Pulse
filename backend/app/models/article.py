from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, TEXT, TIMESTAMP, ForeignKey, String, Boolean, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.config import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    url: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False, index=True)
    content: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    summary: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    author: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="rss"
    )
    external_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )
    # 语义向量：512 维（BAAI/bge-small-zh-v1.5，本地推理无需 API Key）
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(512), nullable=True, comment="文章语义向量，用于 RAG 相似度检索"
    )
    importance_score: Mapped[int] = mapped_column(Integer, default=50)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, comment="收藏")
    is_liked: Mapped[bool] = mapped_column(Boolean, default=False, comment="喜欢")
    notes: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    insight: Mapped[str | None] = mapped_column(TEXT, nullable=True, comment="AI 生成的个人关联洞察")
    process_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="pending", comment="pending/processing/done/failed"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
        comment="首次标记已读的时间，用于浏览历史记录"
    )
