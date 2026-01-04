from datetime import datetime
from sqlmodel import Field, SQLModel


class ImageLineage(SQLModel, table=True):
    parent_id: int | None = Field(
        default=None, foreign_key="localimage.id", primary_key=True)
    child_id: int | None = Field(
        default=None, foreign_key="localimage.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
