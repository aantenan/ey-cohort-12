from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    """Claims extracted from a validated Entra ID access token."""

    sub: str
    oid: str | None = Field(default=None, description="Object ID when present in token")
    email: str | None = None
    name: str | None = None
    roles: list[str] = Field(default_factory=list)
