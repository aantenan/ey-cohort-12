"""slowapi limiter: per-IP or per-token `sub` (unverified decode for keying only)."""

import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return get_remote_address(request)
    token = auth.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["RS256", "HS256"],
        )
        sub = payload.get("sub")
        if isinstance(sub, str) and sub:
            return f"user:{sub}"
    except Exception:
        pass
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
