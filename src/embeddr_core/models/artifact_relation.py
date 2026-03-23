from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, JSON, SQLModel


class ArtifactRelation(SQLModel, table=True):
    """
    Typed, semantic edge between two artifacts.

    Examples:
        - A "cover_image" for B
        - A "generated_by" B (workflow provenance)
        - A "tagged_with" B (tag entity)

    Distinct from ArtifactLineage, which tracks physical creation history
    linked to executions. Relations are declarative semantic connections,
    created by users, plugins, or agents.

    source_namespace identifies who created the relation:
        "user"          — created directly by a user
        "plugin:stash"  — created by the stash plugin
        "agent:xyz"     — created by an agent
        "system:auto"   — created automatically by the system
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    source_id: UUID = Field(foreign_key="artifact.id", index=True, nullable=False)
    target_id: UUID = Field(foreign_key="artifact.id", index=True, nullable=False)

    # The relation type name — must be a registered RelationTypeDef name,
    # or a plugin-defined type. Free-form strings are allowed for forwards
    # compatibility but unknown types resolve to the "other" family.
    relation_type: str = Field(index=True, nullable=False)

    # Who declared this relation. Namespaced by creator class:
    # "user", "plugin:<name>", "agent:<name>", "system:<subsystem>"
    source_namespace: str = Field(default="user", index=True, nullable=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Optional confidence / strength of the relation (0.0 – 1.0).
    # Useful for similarity relations, agent-inferred links, etc.
    weight: Optional[float] = Field(default=None)

    # Open-ended edge attributes. Plugins can store domain-specific
    # metadata here (e.g. page range for a "cited_in" relation).
    metadata_json: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    __table_args__ = (
        # Enforce uniqueness on the logical edge key.
        # (source, target, type, namespace) together uniquely identify an edge.
        UniqueConstraint(
            "source_id",
            "target_id",
            "relation_type",
            "source_namespace",
            name="uq_artifactrelation_edge",
        ),
        Index("ix_artifactrelation_relation_type_ns", "relation_type", "source_namespace"),
    )
