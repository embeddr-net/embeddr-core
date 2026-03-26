from typing import Optional, List, Dict, Any, Set

from pydantic import BaseModel, Field as PydanticField, model_validator
from sqlmodel import Field, SQLModel, JSON, Relationship, Session


class ArtifactType(SQLModel, table=True):
    """
    Defines a category of Artifacts (e.g. "image:comfy", "text:book").
    Acts as a template for capabilities and behavior.
    """
    name: str = Field(primary_key=True, index=True)

    # Inheritance: Allows "image:comfy" to extend "image"
    parent_name: Optional[str] = Field(
        default=None, foreign_key="artifacttype.name", index=True)

    # Core capabilities provided by this type
    # e.g. ["renderable", "embeddable:vision"]
    default_capabilities: List[str] = Field(default_factory=list, sa_type=JSON)

    # Human readable description
    description: Optional[str] = None

    # Type-level metadata (e.g. is_container=True, icon="book")
    metadata_json: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Relationships
    parent: Optional["ArtifactType"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "ArtifactType.name"
        }
    )

    # We will likely access children types or artifacts, but not strictly required here yet.

    def resolve_capabilities(self, session: Session) -> List[str]:
        """
        Recursively resolves capabilities by walking up the parent tree.
        """
        caps: Set[str] = set(self.default_capabilities)

        current_type = self
        while current_type.parent_name:
            # Try to fetch parent from relationship first if loaded
            if current_type.parent:
                current_type = current_type.parent
            else:
                # If not loaded, fetch from session
                parent = session.get(ArtifactType, current_type.parent_name)
                if not parent:
                    break
                current_type = parent

            caps.update(current_type.default_capabilities)

        return list(caps)


class ArtifactTypeSpec(BaseModel):
    """
    Declarative artifact type definition registered by plugins.
    """

    name: str
    parent_name: Optional[str] = None
    description: Optional[str] = None
    default_capabilities: List[str] = PydanticField(default_factory=list)
    metadata_json: Dict[str, Any] = PydanticField(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, values):
        """Accept common field name variants from plugins."""
        if isinstance(values, dict):
            if "name" not in values and "type_name" in values:
                values["name"] = values.pop("type_name")
            if "parent_name" not in values and "base_type_name" in values:
                values["parent_name"] = values.pop("base_type_name")
        return values
