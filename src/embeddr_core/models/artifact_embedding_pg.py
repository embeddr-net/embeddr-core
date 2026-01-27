from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

try:
    from pgvector.sqlalchemy import Vector
except ImportError as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "pgvector is required for ArtifactEmbeddingPg. Install 'pgvector'."
    ) from exc


class ArtifactEmbeddingPg(SQLModel, table=True):
    """
    Stores vector embeddings in Postgres pgvector for fast similarity search.
    """

    __tablename__ = "artifact_embedding_pg"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    model_name: str = Field(index=True)
    space: str = Field(default="default", index=True)
    vector_dim: int
    vector: List[float] = Field(sa_type=Vector())

    plugin_name: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "arbitrary_types_allowed": True,
    }
