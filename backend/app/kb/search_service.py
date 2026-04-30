"""Full-text KB search (PostgreSQL `tsvector` / SQLite fallback) with optional Redis cache (WO-27)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import and_, or_, text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models.kb_article import ArticleStatus, KBArticle
from app.db.models.ticket_category import TicketCategory

KB_SEARCH_CACHE_PREFIX = "kb:search:v1:"
KB_SEARCH_CACHE_TTL_S = 300


def _cache_key(q: str, category_id: UUID | None) -> str:
    raw = f"{q.strip().lower()}|{category_id.hex if category_id else ''}"
    return KB_SEARCH_CACHE_PREFIX + hashlib.sha256(raw.encode()).hexdigest()


def _json_default(obj: object) -> str | float:
    """Serialize cache payloads (UUID/datetime/Decimal are not JSON-native)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(type(obj).__name__)


def _sqlite_snippet(content: str, query: str, max_len: int = 320) -> str:
    words = [w for w in re.split(r"\s+", query.strip()) if w]
    if not words:
        return (content or "")[:max_len]
    lower = (content or "").lower()
    for w in words:
        idx = lower.find(w.lower())
        if idx >= 0:
            start = max(0, idx - 80)
            frag = content[start : start + max_len]
            # rough highlight of first token match
            pattern = re.compile(re.escape(w), re.IGNORECASE)
            frag = pattern.sub(lambda m: f"<b>{m.group(0)}</b>", frag, count=1)
            return frag
    return (content or "")[:max_len]


async def _search_postgres(
    session: AsyncSession,
    *,
    q: str,
    category_id: UUID | None,
) -> list[dict[str, Any]]:
    safe_q = q.replace("\x00", "")
    base_select = """
        SELECT
          a.id AS article_id,
          a.title,
          ts_headline(
            'english',
            coalesce(a.content, ''),
            plainto_tsquery('english', :q),
            'StartSel=<b>, StopSel=</b>, MaxWords=35, MinWords=15'
          ) AS snippet,
          c.name AS category,
          a.published_at,
          ts_rank(a.search_vector, plainto_tsquery('english', :q)) AS rank
        FROM kb_article a
        LEFT JOIN ticket_category c ON c.id = a.category_id
        WHERE a.status = 'published'
          AND a.search_vector @@ plainto_tsquery('english', :q)
    """
    if category_id is not None:
        sql = text(base_select + " AND a.category_id = :category_id ORDER BY rank DESC")
        result = await session.execute(sql, {"q": safe_q, "category_id": category_id})
    else:
        sql = text(base_select + " ORDER BY rank DESC")
        result = await session.execute(sql, {"q": safe_q})
    rows = result.mappings().all()
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "article_id": row["article_id"],
                "title": row["title"],
                "snippet": row["snippet"] or "",
                "category": row["category"],
                "published_at": row["published_at"],
                "rank": float(row["rank"] or 0.0),
            }
        )
    return out


async def _search_sqlite(
    session: AsyncSession,
    *,
    q: str,
    category_id: UUID | None,
) -> list[dict[str, Any]]:
    words = [w for w in re.split(r"\s+", q.strip()) if w]
    if not words:
        return []
    conditions: list[Any] = [KBArticle.status == ArticleStatus.published]
    if category_id is not None:
        conditions.append(KBArticle.category_id == category_id)
    for w in words:
        term = f"%{w}%"
        conditions.append(or_(KBArticle.title.ilike(term), KBArticle.content.ilike(term)))
    stmt = (
        select(KBArticle, TicketCategory.name)
        .outerjoin(TicketCategory, TicketCategory.id == KBArticle.category_id)
        .where(and_(*conditions))
    )
    rows = (await session.exec(stmt)).all()
    out: list[dict[str, Any]] = []
    for article, cat_name in rows:
        out.append(
            {
                "article_id": article.id,
                "title": article.title,
                "snippet": _sqlite_snippet(article.content, q),
                "category": cat_name,
                "published_at": article.published_at,
                "rank": 1.0,
            }
        )
    return out


async def search_kb_articles_cached(
    session: AsyncSession,
    *,
    q: str,
    category_id: UUID | None,
    redis: Redis | None,
) -> list[dict[str, Any]]:
    """Return full ranked result list (caller paginates). Uses Redis for (q, category_id) cache."""
    key = _cache_key(q, category_id)
    if redis is not None:
        raw = await redis.get(key)
        if raw is not None:
            blob = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
            data = json.loads(blob)
            return data["items"]

    conn = await session.connection()
    dialect = conn.engine.dialect.name
    if dialect == "postgresql":
        items = await _search_postgres(session, q=q, category_id=category_id)
    else:
        items = await _search_sqlite(session, q=q, category_id=category_id)

    if redis is not None:
        await redis.set(
            key,
            json.dumps({"items": items}, default=_json_default).encode(),
            ex=KB_SEARCH_CACHE_TTL_S,
        )
    return items
