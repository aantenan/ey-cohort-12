from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KBArticleFeedback(SQLModel, table=True):
    __tablename__ = "kb_article_feedback"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    article_id: UUID = Field(foreign_key="kb_article.id")
    submitted_by_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    # ChatSession FK deferred to chat WO — store nullable UUID for linkage
    chat_session_id: UUID | None = Field(default=None)
    was_helpful: bool = Field()
    submitted_at: datetime = Field(default_factory=_utcnow)
