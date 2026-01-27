from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, JSON
from sqlalchemy import Index


class ArtifactFeatureRef(SQLModel, table=True):
    """
    Stores lightweight references to plugin-generated features for artifacts.
    Payloads live in plugin-managed stores; core only tracks metadata + pointers.
    """

    __tablename__ = "artifactfeature"
    __table_args__ = (
        Index(
            "ix_artifactfeature_artifact_feature_name",
            "artifact_id",
            "feature_type",
            "name",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    # Feature type (e.g. "embedding", "caption", "ocr", "hash")
    feature_type: str = Field(index=True)

    # Feature name (e.g. "clip-vit-b32:visual")
    name: str = Field(index=True)

    # Plugin that produced the feature
    producer_plugin: Optional[str] = Field(default=None, index=True)
    producer_version: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    schema_version: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None, index=True)

    # Storage location for the feature payload
    storage_kind: str = Field(index=True)
    storage_ref: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Optional embedding metadata for quick filtering
    model_name: Optional[str] = Field(default=None, index=True)
    space: Optional[str] = Field(default=None, index=True)
    vector_dim: Optional[int] = None

    # Extra metadata (namespaced)
    metadata_json: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
