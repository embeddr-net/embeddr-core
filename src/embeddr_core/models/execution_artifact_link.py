from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ExecutionArtifactLink(SQLModel, table=True):
    """
    Tracks which artifacts an execution touched (created, modified, deleted, read, input).

    Enables bidirectional queries:
      - "What did execution X do?" → list linked artifacts
      - "Why does artifact Y exist?" → find creating execution
      - "What modified artifact Y?" → find all modifying executions
    """
    __tablename__ = "execution_artifact_link"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    execution_id: UUID = Field(foreign_key="artifactexecution.id", index=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    # Action performed: "created" | "modified" | "deleted" | "read" | "input"
    action: str = Field(index=True)

    # Optional context about the link (e.g. "added tag 'landscape'")
    detail: Optional[str] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
