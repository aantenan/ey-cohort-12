from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArticleStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class KBArticle(SQLModel, table=True):
    __tablename__ = "kb_article"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=500)
    content: str = Field(sa_column=Column(Text, nullable=False))
    category_id: UUID | None = Field(default=None, foreign_key="ticket_category.id")
    author_id: UUID = Field(foreign_key="app_user.id")
    status: ArticleStatus = Field(default=ArticleStatus.draft)
    published_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
