"""Import all SQLModel table classes for Alembic metadata."""

from sqlmodel import SQLModel

from app.db.models.kb_article import ArticleStatus, KBArticle
from app.db.models.kb_article_feedback import KBArticleFeedback
from app.db.models.ticket_category import TicketCategory
from app.db.models.user import User

__all__ = [
    "SQLModel",
    "ArticleStatus",
    "KBArticle",
    "KBArticleFeedback",
    "TicketCategory",
    "User",
]
