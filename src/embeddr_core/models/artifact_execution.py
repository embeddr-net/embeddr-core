from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON, Column


class ArtifactExecution(SQLModel, table=True):
    """
    Represents a tracked execution of a plugin action or system job.
    Every action — ingestion, tool calls, uploads, automation — creates one of these.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Job Type Identifier (e.g. "comfy.generate", "thumbnail.create", "core.ingest.batch")
    type: str = Field(index=True)

    # Originating Plugin (for accounting/logging)
    plugin_name: str = Field(index=True)

    # pending, running, completed, failed, canceled, waiting
    status: str = Field(index=True, default="pending")

    # cpu, gpu, io, network — used for semaphore-based routing
    resource_class: str = Field(default="cpu")

    # Higher is more important
    priority: int = Field(default=0, index=True)

    # 0-100 integer percentage
    progress: int = Field(default=0)

    # Human readable status message (e.g. "Loading checkpoints...")
    message: str = Field(default="")

    # user, system, automation, lotus
    trigger: str = Field(default="user")

    # Opaque inputs payload
    inputs: Dict[str, Any] = Field(default={}, sa_type=JSON)

    # Outcome payload (artifact IDs, stats)
    outputs: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    # Linking to related artifacts (optional)
    primary_artifact_id: Optional[UUID] = Field(
        default=None, foreign_key="artifact.id", index=True)

    # Parent execution (optional, for nested/parallel tracking)
    parent_execution_id: Optional[UUID] = Field(
        default=None, foreign_key="artifactexecution.id", index=True)

    # --- Provenance & Operator tracking ---

    # Who initiated this execution (operator UUID or system identity)
    operator_id: Optional[UUID] = Field(default=None, index=True)

    # Which API key was used (for audit trail)
    api_key_id: Optional[str] = Field(default=None)

    # What event triggered this (e.g. "artifact.created", "user.action")
    trigger_event_type: Optional[str] = Field(default=None)

    # Arbitrary tags for filtering/grouping (e.g. {"category": "ingestion", "batch_id": "xxx"})
    tags: Dict[str, str] = Field(default={}, sa_column=Column(JSON))

    # --- Timestamps ---

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    error: Optional[str] = None
