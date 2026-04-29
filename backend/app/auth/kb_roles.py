"""Role helpers for Knowledge Base permissions (JWT `roles` / `groups` claims)."""

from __future__ import annotations

from app.auth.models import CurrentUser


def _norm_roles(user: CurrentUser) -> set[str]:
    return {r.lower() for r in user.roles}


def is_kb_staff(user: CurrentUser) -> bool:
    """Agents and managers may view draft/archived articles."""
    return bool(
        _norm_roles(user)
        & {
            "level1_agent",
            "level2_agent",
            "agent",
            "manager",
            "admin",
        }
    )


def is_manager(user: CurrentUser) -> bool:
    return bool(_norm_roles(user) & {"manager", "admin"})


def can_create_kb_articles(user: CurrentUser) -> bool:
    """Level-1 agent or higher (managers, admins, level2 agents)."""
    return bool(
        _norm_roles(user)
        & {
            "level1_agent",
            "level2_agent",
            "manager",
            "admin",
        }
    )


def is_agent_role(user: CurrentUser) -> bool:
    """Broad agent family (excludes end-users with no agent claims)."""
    return bool(
        _norm_roles(user)
        & {
            "level1_agent",
            "level2_agent",
            "agent",
        }
    )
