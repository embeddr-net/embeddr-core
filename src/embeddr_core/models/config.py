from typing import Optional
from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel, UniqueConstraint


class AutoAnalysisConfig(SQLModel, table=True):
    """
    Configuration for auto-analysis plugins.
    Prioritizes collection-specific settings over global settings.
    """
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", "plugin_name",
                         name="unique_analysis_config"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    # "global" or "collection"
    scope: str = Field(default="global", index=True)
    # Collection ID or None for global
    scope_id: Optional[UUID] = Field(default=None, index=True)
    # The identifier for the analysis/plugin (e.g. "embeddr-thumbnailer")
    plugin_name: str = Field(index=True)
    enabled: bool = Field(default=True)
    priority: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
