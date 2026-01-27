from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, JSON


class PluginConfig(SQLModel, table=True):
    """
    A single config blob for a plugin at a given scope.
    Start with scope='global'. Add per-user/per-workspace later.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    plugin_name: str = Field(index=True)
    config_id: str = Field(default="default", index=True)
    # global | user | workspace | instance
    scope: str = Field(index=True, default="global")
    scope_id: Optional[str] = Field(default=None, index=True)

    # JSON blob stored for the config values
    value: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
