from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON


class Automation(SQLModel, table=True):
    """
    Defines a reactive rule in the system.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    is_active: bool = Field(default=True)

    # Event that triggers this automation (e.g., "artifact.created", "relation.added")
    trigger_event: str = Field(index=True)

    # JSON logic/filtering to apply to the event payload
    # e.g. { "type": "image", "metadata.has_face": true }
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Work to perform
    # e.g. { "job_type": "comfy.generate", "inputs": { ... } }
    actions: List[Dict[str, Any]] = Field(default_factory=list, sa_type=JSON)

    # Optional metadata for UI/editor state (e.g. pipeline inputs schema)
    metadata_json: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
