"""Resolve Entra token identity to persistent `app_user` rows."""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import CurrentUser
from app.db.models.user import User


async def get_or_create_app_user(session: AsyncSession, cu: CurrentUser) -> User:
    key = (cu.oid or cu.sub or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Token missing user identity (oid/sub)")
    result = await session.exec(select(User).where(User.entra_object_id == key))
    existing = result.first()
    if existing:
        return existing
    user = User(entra_object_id=key, email=cu.email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
