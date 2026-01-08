from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON


class ArtifactEmbedding(SQLModel, table=True):
    """
    Stores vector embeddings for artifacts.
    Decouples the heavy vector data from the core artifact table.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    # Embedding model used, e.g. "clip-vit-base-patch32", "jina-embeddings-v2"
    model_name: str = Field(index=True)

    # Which plugin generated this?
    plugin_name: Optional[str] = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # The dimension of the vector, e.g. 512, 768
    vector_dim: int

    # The vector itself. Stored as JSON list of floats for now.
    # In Postgres with pgvector, this would be mapped to a VECTOR type.
    vector_json: List[float] = Field(sa_type=JSON)

    # Optional: which "space" this embedding belongs to, e.g. "visual", "semantic"
    space: str = Field(default="default", index=True)
