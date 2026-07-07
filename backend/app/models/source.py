from datetime import datetime

from sqlalchemy import Integer, String, TEXT, TIMESTAMP, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.config import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(TEXT, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # rss / arxiv / website / github / twitter
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    last_fetched: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reliability_score: Mapped[int] = mapped_column(Integer, default=70)
    extra_config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
