from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON


class ArtifactExecution(SQLModel, table=True):
    """
    Represents a tracked execution of a plugin action or system job.
    This replaces the concept of 'Generation' with a generic execution model.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Job Type Identifier (e.g. "comfy.generate", "thumbnail.create")
    type: str = Field(index=True)

    # Originating Plugin (for accounting/logging)
    plugin_name: str = Field(index=True)

    # pending, running, completed, failed, canceled
    status: str = Field(index=True, default="pending")

    # cpu, gpu, io, network
    resource_class: str = Field(default="cpu")

    # Higher is more important
    priority: int = Field(default=0, index=True)

    # 0-100 integer percentage
    progress: int = Field(default=0)

    # Human readable status message (e.g. "Loading checkpoints...")
    message: str = Field(default="")

    # user, system, automation
    trigger: str = Field(default="user")

    # Opaque inputs payload
    inputs: Dict[str, Any] = Field(default={}, sa_type=JSON)

    # Outcome payload (artifact IDs, stats)
    outputs: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    # Linking to related artifacts (optional)
    primary_artifact_id: Optional[UUID] = Field(
        default=None, foreign_key="artifact.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    error: Optional[str] = None
