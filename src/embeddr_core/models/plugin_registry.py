from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, JSON


class PluginRegistry(SQLModel, table=True):
    """
    Registry of installed/known plugins.
    Used to track which plugins are active, their version, and what they contribute.
    """
    name: str = Field(primary_key=True, index=True)
    version: str

    # Status: "active", "disabled", "deprecated", "missing"
    status: str = Field(default="active", index=True)

    # Plugin Type: "adapter", "workflow", "importer", "exporter"
    plugin_type: str = Field(default="adapter", index=True)

    # Heartbeat
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Information about what this plugin provides
    # e.g. ["image:comfy", "text:story"]
    contributed_types: List[str] = Field(default=[], sa_type=JSON)

    # e.g. ["renderable", "execute_workflow"]
    contributed_capabilities: List[str] = Field(default=[], sa_type=JSON)

    installed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Unstructured config or state for the plugin
    plugin_metadata: Dict[str, Any] = Field(default={}, sa_type=JSON)
