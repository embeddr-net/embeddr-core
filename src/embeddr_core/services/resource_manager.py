from enum import Enum
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)


class ResourceStatus(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    UNLOADING = "unloading"


class ManagedResource(BaseModel):
    id: str  # Unique ID, e.g. "model:qwen-3vl-2b"
    name: str
    plugin_name: str
    type: str  # e.g. "llm", "vlm", "embedding", "vector_store"
    status: ResourceStatus = ResourceStatus.IDLE
    memory_usage_bytes: int = 0
    device: str = "cpu"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)


class ResourceManager:
    """
    Central service to track system resources (models, indexes, etc.)
    used by plugins.
    """

    def __init__(self):
        self._resources: Dict[str, ManagedResource] = {}
        self._unload_handlers = {}

    def register_resource(self, resource: ManagedResource):
        self._resources[resource.id] = resource
        logger.debug(f"Registered resource: {resource.id} ({resource.name})")

    def update_resource(self, resource_id: str, **kwargs):
        if resource_id in self._resources:
            for k, v in kwargs.items():
                if hasattr(self._resources[resource_id], k):
                    setattr(self._resources[resource_id], k, v)
            self._resources[resource_id].last_updated = datetime.now()

    def unregister_resource(self, resource_id: str):
        if resource_id in self._resources:
            del self._resources[resource_id]

    def list_resources(self) -> List[ManagedResource]:
        return list(self._resources.values())

    def get_resource(self, resource_id: str) -> Optional[ManagedResource]:
        return self._resources.get(resource_id)

    def get_total_memory_usage(self) -> int:
        """
        Return total known memory usage in bytes across all managed resources.
        """
        return sum(r.memory_usage_bytes for r in self._resources.values() if r.status == ResourceStatus.LOADED)

    def register_unload_handler(self, resource_id: str, handler: callable):
        self._unload_handlers[resource_id] = handler

    def request_unload(self, resource_id: str):
        if resource_id in self._unload_handlers:
            self.update_resource(resource_id, status=ResourceStatus.UNLOADING)
            try:
                self._unload_handlers[resource_id]()
                self.update_resource(
                    resource_id, status=ResourceStatus.IDLE, memory_usage_bytes=0)
                logger.info(f"Successfully unloaded resource: {resource_id}")
            except Exception as e:
                logger.error(f"Failed to unload resource {resource_id}: {e}")
                self.update_resource(resource_id, status=ResourceStatus.ERROR)


# Global instances of Enums needed by classes above if not imported properly

resource_manager = ResourceManager()
