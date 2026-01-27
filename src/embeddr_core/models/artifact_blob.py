from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ArtifactBlob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    storage_backend: str = Field(default="local", index=True)
    path: str
    sha256: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
