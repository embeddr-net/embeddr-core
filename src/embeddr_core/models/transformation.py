from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, JSON


class Transformation(SQLModel, table=True):
    """
    Records a discrete event that produced artifacts from other artifacts.
    Captures 'what' happened (parameters), not 'how' (adapter internals).
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # What plugin/adapter performed this? e.g. "embeddr-comfyui"
    plugin_name: Optional[str] = Field(default=None, index=True)

    # What task was performed? e.g. "comfy_workflow_execution", "image_resize"
    task_name: Optional[str] = Field(default=None, index=True)

    # Status: "pending", "completed", "failed"
    status: str = Field(default="completed", index=True)

    # Metadata about the transformation event
    # e.g. { "adapter": "comfyui", "duration_ms": 500 }
    metadata_json: Dict[str, Any] = Field(default={}, sa_type=JSON)
