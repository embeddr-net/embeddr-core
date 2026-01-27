from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, JSON


class ArtifactExecutionEvent(SQLModel, table=True):
    """
    Append-only log of execution events for traceability.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    execution_id: UUID = Field(foreign_key="artifactexecution.id", index=True)

    # execution.created, execution.started, execution.updated, execution.completed, execution.failed, execution.log
    event_type: str = Field(index=True)

    # info, warning, error, debug
    level: str = Field(default="info", index=True)

    message: str = Field(default="")
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
