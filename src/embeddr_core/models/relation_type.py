from typing import Optional

from sqlmodel import Field, SQLModel


class RelationTypeDef(SQLModel, table=True):
    """
    Registry of known relation types.

    Core types ("contains", "group", "part_of", "reference", "generates")
    are seeded at startup. Plugins register additional types via
    PluginContext.register_relation_type() during on_load().

    This replaces the hardcoded _EXPLICIT_RELATION_SEMANTICS dict in
    graph_semantics.py, which caused plugin-specific types to leak into
    embeddr-core.
    """

    # The canonical name of the relation type, e.g. "contains", "appears_in"
    name: str = Field(primary_key=True)

    # Broad grouping for UI filtering and graph analytics:
    #   containment | semantic | workflow | provenance | attribution
    #   membership  | publishing | agent | state | other
    family: str = Field(default="other", index=True)

    # Optional inverse relation name, e.g. "contains" <-> "contained_in"
    inverse: Optional[str] = Field(default=None)

    # Whether the relation is transitive (A→B, B→C implies A→C)
    transitive: bool = Field(default=False)

    # Structural relations define the artifact hierarchy tree.
    # Non-structural relations are semantic / contextual.
    structural: bool = Field(default=False)

    # Human-readable description shown in UI taxonomy views.
    description: str = Field(default="")

    # Who registered this type:
    #   "core"          — built-in, always present
    #   "plugin:<name>" — registered by a plugin during on_load
    registered_by: str = Field(default="core", index=True)
