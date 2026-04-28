"""Domain router placeholder: authenticated samples (`/me`, RBAC)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user, require_roles
from app.auth.models import CurrentUser

router = APIRouter(prefix="/common", tags=["common"])


@router.get("/me")
def read_me(current: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, object]:
    return current.model_dump()


@router.get("/admin/ping")
def admin_only(_user: Annotated[CurrentUser, Depends(require_roles("Admin"))]) -> dict[str, str]:
    return {"role_check": "passed"}
