"""JWT validation against Microsoft Entra ID JWKS."""

from __future__ import annotations

import jwt
from jwt import PyJWKClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.models import CurrentUser
from app.core.config import Settings

_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_client(settings: Settings) -> PyJWKClient:
    url = settings.jwks_url
    if url not in _jwks_clients:
        _jwks_clients[url] = PyJWKClient(url, cache_keys=True)
    return _jwks_clients[url]


def _extract_roles(payload: dict[str, object]) -> list[str]:
    roles: list[str] = []
    raw_roles = payload.get("roles")
    if isinstance(raw_roles, list):
        roles.extend(str(r) for r in raw_roles)
    elif isinstance(raw_roles, str):
        roles.append(raw_roles)

    groups = payload.get("groups")
    if isinstance(groups, list):
        roles.extend(str(g) for g in groups)

    single = payload.get("role")
    if isinstance(single, str):
        roles.append(single)

    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for r in roles:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def validate_access_token(token: str, settings: Settings) -> CurrentUser:
    if not settings.jwks_url or not settings.entra_audience:
        raise StarletteHTTPException(
            status_code=503,
            detail="JWT validation is not configured (ENTRA_TENANT_ID / ENTRA_AUDIENCE)",
        )
    issuer = settings.expected_issuer
    if not issuer:
        raise StarletteHTTPException(
            status_code=503,
            detail="Cannot determine token issuer (configure ENTRA_TENANT_ID or ENTRA_ISSUER)",
        )

    try:
        jwks = _jwks_client(settings)
        signing_key = jwks.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_audience,
            issuer=issuer,
            options={"verify_aud": True, "verify_exp": True},
        )
    except jwt.ExpiredSignatureError as e:
        raise StarletteHTTPException(status_code=401, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise StarletteHTTPException(status_code=401, detail="Invalid token") from e
    except Exception as e:
        raise StarletteHTTPException(status_code=401, detail="Token validation failed") from e

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise StarletteHTTPException(status_code=401, detail="Token missing subject")

    oid = payload.get("oid")
    email = payload.get("email") or payload.get("preferred_username")
    name = payload.get("name")

    return CurrentUser(
        sub=sub,
        oid=str(oid) if oid is not None else None,
        email=str(email) if email else None,
        name=str(name) if name else None,
        roles=_extract_roles(payload),
    )
