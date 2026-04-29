from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Application user linked to Entra object id / subject."""

    __tablename__ = "app_user"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    entra_object_id: str = Field(unique=True, index=True, max_length=64)
    email: str | None = Field(default=None, max_length=320)
