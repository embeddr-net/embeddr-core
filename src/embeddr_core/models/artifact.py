from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON, Relationship
from .artifact_type import ArtifactType


class Artifact(SQLModel, table=True):
    """
    Core Artifact entity.
    Represents any user data (file, text, image, etc.)
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Universal resource indicator (optional, for files/urls)
    uri: Optional[str] = Field(default=None, index=True)

    # Type System Link
    type_name: str = Field(foreign_key="artifacttype.name", index=True)

    # Fallback/Base Type (computed, stored for fast filtering)
    base_type_name: str = Field(index=True, default="artifact")

    # Unbounded, namespaced metadata
    # e.g. { "embeddr:image": { "width": 512, ... }, "user:comment": "..." }
    metadata_json: Dict[str, Any] = Field(default={}, sa_type=JSON)

    # Instance-specific capabilities (added on top of Type capabilities)
    # e.g. An image that has been specifically flagged as "nsfw" or "hidden"
    # might effectively "lose" capabilities or gain restriction capabilities locally
    # though usually this is additive.
    override_capabilities: List[str] = Field(default=[], sa_type=JSON)

    # Relationships
    artifact_type: ArtifactType = Relationship()

    def get_base_type_name(self) -> str:
        """
        Returns the name of the immediate parent type, or 'artifact' if none.
        Useful for fallbacks (e.g. if 'image:comfy' is missing, treat as 'image').
        """
        if self.artifact_type and self.artifact_type.parent_name:
            return self.artifact_type.parent_name
        return "artifact"

    @property
    def name(self) -> str | None:
        """Helper to get a display name from metadata."""
        return self.metadata_json.get("name") or self.metadata_json.get("filename")

    def get_effective_capabilities(self, session) -> List[str]:
        """
        Resolves the final list of capabilities for this artifact.
        Combines Type capabilities (resolved recursively) with instance overrides.
        """
        # Start with overrides (always applied)
        caps = set(self.override_capabilities)

        # If the type is loaded, resolve its capabilities
        # Note: This might trigger lazy loading if not eagerly fetched
        if self.artifact_type:
            caps.update(self.artifact_type.resolve_capabilities(session))
        elif self.type_name:
            # Type object not loaded, try to fetch it
            # This requires passing the session to this method
            from .artifact_type import ArtifactType
            # Use local import to avoid circular dependency
            a_type = session.get(ArtifactType, self.type_name)
            if a_type:
                caps.update(a_type.resolve_capabilities(session))

        return list(caps)


class ArtifactPreview(SQLModel, table=True):
    """
    Stores derived preview representations of artifacts
    (thumbnails, low-res previews, waveforms, etc.)
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    # e.g. "thumbnail", "preview", "waveform"
    preview_type: str = Field(index=True)

    # e.g. "image/jpeg", "image/webp"
    mime_type: str

    # Where the preview lives
    uri: str

    # Size metadata (optional but useful)
    width: Optional[int] = None
    height: Optional[int] = None

    plugin_name: Optional[str] = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
