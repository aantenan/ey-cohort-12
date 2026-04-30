from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.kb_article import ArticleStatus


class KBArticleRead(BaseModel):
    id: UUID
    title: str
    content: str
    category_id: UUID | None
    author_id: UUID
    status: ArticleStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KBArticleCreate(BaseModel):
    title: str = Field(max_length=500)
    content: str
    category_id: UUID | None = None


class KBArticlePatch(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    content: str | None = None
    category_id: UUID | None = None
    status: ArticleStatus | None = None


class KBFeedbackCreate(BaseModel):
    was_helpful: bool
    chat_session_id: UUID | None = None


class KBSearchHit(BaseModel):
    article_id: UUID
    title: str
    snippet: str
    category: str | None = None
    published_at: datetime | None = None
    rank: float


class KBSearchResponse(BaseModel):
    data: list[KBSearchHit]
    total: int
    limit: int
    offset: int


class CategoryRead(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class KBArticleAdminRead(KBArticleRead):
    """Article row for KB staff admin list (includes aggregate feedback)."""

    feedback_count: int = 0
    helpful_percent: float | None = None
