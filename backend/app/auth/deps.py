from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import validate_access_token
from app.auth.models import CurrentUser
from app.core.config import Settings, get_settings

oauth_scheme = HTTPBearer(auto_error=False)

# Synthetic identity when Settings.auth_disabled is true (local dev only).
LOCAL_DEV_USER = CurrentUser(
    sub="local-dev",
    oid="local-dev-oid",
    email="dev@local.invalid",
    name="Local Dev",
    roles=["admin", "manager", "level1_agent", "level2_agent", "agent"],
)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(oauth_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if settings.auth_disabled:
        return LOCAL_DEV_USER
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return validate_access_token(credentials.credentials, settings)


async def get_current_user_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(oauth_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser | None:
    if settings.auth_disabled:
        return LOCAL_DEV_USER
    if credentials is None:
        return None
    return validate_access_token(credentials.credentials, settings)


def require_roles(*allowed_roles: str):
    """Dependency factory: 403 if the user has none of the allowed roles (or group IDs)."""

    allowed = set(allowed_roles)

    async def _require(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if not allowed.intersection(set(user.roles)):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return _require
