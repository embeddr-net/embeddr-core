from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel

from .artifact import Artifact


class Collection(SQLModel, table=True):
    """
    A user-defined grouping of artifacts.
    Replaces the old 'Collection' which was image-specific.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    items: List["CollectionItem"] = Relationship(
        back_populates="collection",
        sa_relationship_kwargs={"cascade": "all, delete"}
    )


class CollectionItem(SQLModel, table=True):
    """
    Link table between Collection and Artifact.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: UUID = Field(foreign_key="collection.id")
    artifact_id: UUID = Field(foreign_key="artifact.id")
    added_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    collection: Collection = Relationship(back_populates="items")
    # We don't necessarily need a back_populates on Artifact unless we want to access collections from artifact frequently
    artifact: Artifact = Relationship()
