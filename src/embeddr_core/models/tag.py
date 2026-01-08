from datetime import datetime
from uuid import UUID
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class ArtifactTagLink(SQLModel, table=True):
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", primary_key=True)


class Tag(SQLModel, table=True):
    """
    First-class organization label.
    """
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    # E.g. "manual", "auto:classifier", "import"
    source: str = Field(default="user", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # We don't necessarily need to load all artifacts for a tag within the model
    # but the link table exists for joins.
