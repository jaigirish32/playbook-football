from datetime import datetime
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base


class AICache(Base):
    __tablename__ = "ai_cache"

    question_hash : Mapped[str]      = mapped_column(String(64), primary_key=True)
    question      : Mapped[str]      = mapped_column(Text, nullable=False)
    response      : Mapped[str]      = mapped_column(Text, nullable=False)
    created_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<AICache {self.question_hash}>"