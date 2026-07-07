from datetime import datetime

from sqlalchemy import TIMESTAMP, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.config import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # preferences: {"enabled_sources": ["arxiv_ai", "hackernews"], "interests": ["LLM"]}
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
