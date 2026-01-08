from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, JSON


class ArtifactLineage(SQLModel, table=True):
    """
    Records the parent-child relationship between artifacts.
    Represents the directed graph of creation.
    """
    parent_id: UUID = Field(foreign_key="artifact.id", primary_key=True)
    child_id: UUID = Field(foreign_key="artifact.id", primary_key=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata about THIS specific edge (e.g. "used as style reference" vs "used as initial image")
    relationship_metadata: Dict[str, Any] = Field(default={}, sa_type=JSON)

    # Link to the transformation event that created this relationship
    transformation_id: Optional[UUID] = Field(
        default=None, foreign_key="transformation.id", index=True)
