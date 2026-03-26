from datetime import datetime, timezone
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

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata about THIS specific edge (e.g. "used as style reference" vs "used as initial image")
    relationship_metadata: Dict[str, Any] = Field(
        default_factory=dict, sa_type=JSON)

    # Link to the execution event that created this relationship
    execution_id: Optional[UUID] = Field(
        default=None, foreign_key="artifactexecution.id", index=True)
