from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, JSON


class ArtifactIngest(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    status: str = Field(default="pending", index=True)
    storage_backend: str = Field(default="local", index=True)
    storage_path: Optional[str] = None

    content_type: Optional[str] = None
    size: Optional[int] = None
    original_filename: Optional[str] = None

    meta_json: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
