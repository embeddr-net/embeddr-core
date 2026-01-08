from datetime import datetime
from uuid import UUID
from typing import Optional
from sqlmodel import Field, SQLModel


class ArtifactRelation(SQLModel, table=True):
    """
    Semantic, typed connection between two artifacts.
    e.g. A is a "cover_image" for B (book text).
    Distinct from Lineage (which is physical creation history).
    """
    source_id: UUID = Field(foreign_key="artifact.id", primary_key=True)
    target_id: UUID = Field(foreign_key="artifact.id", primary_key=True)

    # Relation Type (e.g. "reference", "part_of", "variant_of")
    relation_type: str = Field(index=True)

    # Plugin namespace/source (e.g. "user", "plugin:books", "auto:similarity")
    source_namespace: Optional[str] = Field(default="user", index=True)
