from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class AnalysisCapability(BaseModel):
    """
    Metadata for a plugin that supports auto-analysis.
    """
    name: str  # The registered action name (e.g. "generate_thumbnail")
    label: str  # Display name
    supported_types: List[str] = []  # "image", "video", "audio", "document"
    trigger_event: str = "artifact.created"  # Default trigger
    priority: int = 10  # Higher runs first
    async_execution: bool = True  # Should be queued or run sync?
    # If > 1, the action supports batching and expects 'artifact_ids' list input
    batch_size: int = 1
