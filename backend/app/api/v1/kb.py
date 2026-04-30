"""Knowledge Base article CRUD, full-text search (WO-27), and feedback (WO-25)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, or_
from sqlmodel import select

from app.api.schema import PaginatedResponse
from app.api.v1.kb_schemas import (
    CategoryRead,
    KBFeedbackCreate,
    KBArticleAdminRead,
    KBArticleCreate,
    KBArticlePatch,
    KBArticleRead,
    KBSearchHit,
    KBSearchResponse,
)
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
from app.db.models.ticket_category import TicketCategory
from app.db.session import SessionDep
from app.kb.search_service import search_kb_articles_cached
from app.kb.users import get_or_create_app_user

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _scalar_count_first(count_val: object | None) -> int:
    """Normalize SQLAlchemy/SQLite count() row (int or one-column row)."""
    if count_val is None:
        return 0
    if isinstance(count_val, (int, float)):
        return int(count_val)
    return int(count_val[0])


@router.get("/search", response_model=KBSearchResponse)
async def kb_search(
    request: Request,
    session: SessionDep,
    _: Annotated[CurrentUser, Depends(get_current_user)],
    q: str = Query(..., min_length=1, max_length=500, description="Search terms"),
    category_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
) -> KBSearchResponse:
    """Ranked full-text search over published KB articles (PostgreSQL FTS; SQLite fallback)."""
    redis = getattr(request.app.state, "redis", None)
    raw_items = await search_kb_articles_cached(
        session, q=q, category_id=category_id, redis=redis
    )
    total = len(raw_items)
    page = raw_items[offset : offset + limit]
    data = [KBSearchHit.model_validate(row) for row in page]
    return KBSearchResponse(data=data, total=total, limit=limit, offset=offset)


@router.get("/categories", response_model=list[CategoryRead])
async def list_kb_categories(
    session: SessionDep,
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[CategoryRead]:
    """Ticket categories for KB article assignment (dropdowns)."""
    stmt = select(TicketCategory).order_by(TicketCategory.name)
    rows = (await session.exec(stmt)).all()
    return [CategoryRead.model_validate(r) for r in rows]


@router.get("/admin/articles", response_model=PaginatedResponse)
async def list_kb_admin_articles(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    status: ArticleStatus | None = Query(
        default=None,
        description="Filter by article status (draft / published / archived)",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse:
    """All KB articles with feedback aggregates — agents and managers only."""
    if not is_kb_staff(user):
        raise HTTPException(status_code=403, detail="KB admin access required")

    agg = (
        select(
            KBArticleFeedback.article_id.label("article_id"),
            func.count(KBArticleFeedback.id).label("feedback_count"),
            func.sum(case((KBArticleFeedback.was_helpful.is_(True), 1), else_=0)).label(
                "helpful_sum"
            ),
        )
        .group_by(KBArticleFeedback.article_id)
    ).subquery()

    filters: list = []
    if status is not None:
        filters.append(KBArticle.status == status)

    count_stmt = (
        select(func.count(KBArticle.id))
        .select_from(KBArticle)
        .outerjoin(agg, KBArticle.id == agg.c.article_id)
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
    count_val = (await session.exec(count_stmt)).first()
    total = _scalar_count_first(count_val)

    list_stmt = (
        select(KBArticle, agg.c.feedback_count, agg.c.helpful_sum)
        .outerjoin(agg, KBArticle.id == agg.c.article_id)
    )
    if filters:
        list_stmt = list_stmt.where(*filters)
    list_stmt = (
        list_stmt.order_by(KBArticle.updated_at.desc()).offset(offset).limit(limit)
    )

    rows = (await session.exec(list_stmt)).all()
    data: list[dict] = []
    for row in rows:
        article = row[0]
        fb_count_raw = row[1]
        helpful_raw = row[2]
        fb_count = int(fb_count_raw or 0)
        helpful_sum = int(helpful_raw or 0)
        pct = (helpful_sum / fb_count * 100.0) if fb_count else None
        payload = KBArticleAdminRead.model_validate(article).model_dump()
        payload["feedback_count"] = fb_count
        payload["helpful_percent"] = round(pct, 1) if pct is not None else None
        data.append(payload)

    return PaginatedResponse(data=data, total=total, limit=limit, offset=offset)


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
    total = _scalar_count_first(count_row)

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
