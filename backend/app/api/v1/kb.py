"""Knowledge Base article CRUD and feedback (WO-25)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlmodel import select

from app.api.schema import PaginatedResponse
from app.api.v1.kb_schemas import KBFeedbackCreate, KBArticleCreate, KBArticlePatch, KBArticleRead
from app.auth.deps import get_current_user
from app.auth.kb_roles import (
    can_create_kb_articles,
    is_agent_role,
    is_kb_staff,
    is_manager,
)
from app.auth.models import CurrentUser
from app.db.models.kb_article import ArticleStatus, KBArticle
from app.db.models.kb_article_feedback import KBArticleFeedback
from app.db.session import SessionDep
from app.kb.users import get_or_create_app_user

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _can_patch_article(user: CurrentUser, app_user_id: UUID, article: KBArticle) -> bool:
    if is_manager(user):
        return True
    if article.author_id != app_user_id:
        return False
    if article.status != ArticleStatus.draft:
        return False
    return is_agent_role(user) or can_create_kb_articles(user)


@router.get("/articles", response_model=PaginatedResponse)
async def list_kb_articles(
    session: SessionDep,
    _: Annotated[CurrentUser, Depends(get_current_user)],
    category_id: UUID | None = None,
    q: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
) -> PaginatedResponse:
    """Published articles only; optional category filter and substring search (`q`)."""
    filters = [KBArticle.status == ArticleStatus.published]
    if category_id is not None:
        filters.append(KBArticle.category_id == category_id)
    if q:
        term = f"%{q}%"
        filters.append(or_(KBArticle.title.like(term), KBArticle.content.like(term)))

    count_stmt = select(func.count()).select_from(KBArticle).where(*filters)
    count_row = (await session.exec(count_stmt)).first()
    total = int(count_row[0]) if count_row is not None else 0

    list_stmt = (
        select(KBArticle)
        .where(*filters)
        .order_by(KBArticle.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.exec(list_stmt)).all()
    data = [KBArticleRead.model_validate(a).model_dump() for a in rows]
    return PaginatedResponse(data=data, total=total, limit=limit, offset=offset)


@router.get("/articles/{article_id}", response_model=KBArticleRead)
async def get_kb_article(
    article_id: UUID,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> KBArticleRead:
    article = await session.get(KBArticle, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.status != ArticleStatus.published and not is_kb_staff(user):
        raise HTTPException(status_code=403, detail="Article not visible for your role")
    return KBArticleRead.model_validate(article)


@router.post("/articles", response_model=KBArticleRead, status_code=201)
async def create_kb_article(
    body: KBArticleCreate,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> KBArticleRead:
    if not can_create_kb_articles(user):
        raise HTTPException(status_code=403, detail="Insufficient privilege to create KB articles")
    author = await get_or_create_app_user(session, user)
    article = KBArticle(
        title=body.title,
        content=body.content,
        category_id=body.category_id,
        author_id=author.id,
        status=ArticleStatus.draft,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return KBArticleRead.model_validate(article)


@router.patch("/articles/{article_id}", response_model=KBArticleRead)
async def patch_kb_article(
    article_id: UUID,
    body: KBArticlePatch,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> KBArticleRead:
    article = await session.get(KBArticle, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    app_user = await get_or_create_app_user(session, user)
    if not _can_patch_article(user, app_user.id, article):
        raise HTTPException(status_code=403, detail="Cannot update this article")

    if body.title is not None:
        article.title = body.title
    if body.content is not None:
        article.content = body.content
    if body.category_id is not None:
        article.category_id = body.category_id
    if body.status is not None:
        new_status = body.status
        if new_status == ArticleStatus.published:
            article.status = ArticleStatus.published
            if article.published_at is None:
                article.published_at = _utcnow()
        elif new_status == ArticleStatus.archived:
            article.status = ArticleStatus.archived
        elif new_status == ArticleStatus.draft:
            article.status = ArticleStatus.draft

    article.updated_at = _utcnow()
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return KBArticleRead.model_validate(article)


@router.post("/articles/{article_id}/feedback", status_code=201)
async def submit_kb_feedback(
    article_id: UUID,
    body: KBFeedbackCreate,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, UUID]:
    article = await session.get(KBArticle, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    # Feedback allowed for authenticated users on existing articles (typically published in portal)
    submitter = await get_or_create_app_user(session, user)
    fb = KBArticleFeedback(
        article_id=article_id,
        submitted_by_id=submitter.id,
        chat_session_id=body.chat_session_id,
        was_helpful=body.was_helpful,
    )
    session.add(fb)
    await session.commit()
    await session.refresh(fb)
    return {"id": fb.id}
