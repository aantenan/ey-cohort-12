from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TicketCategory(SQLModel, table=True):
    __tablename__ = "ticket_category"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=255)
