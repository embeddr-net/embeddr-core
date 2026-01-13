from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel
import logging
import inspect

logger = logging.getLogger(__name__)


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str  # Plugin name
    category: str = "embedding"  # embedding, generation, undefined
    description: str = ""
    loaded: bool = False
    metadata: Dict[str, Any] = {}


class ModelRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._models = {}
            cls._instance._loaders = {}  # map model_id -> loader_function
            cls._instance._unloaders = {}  # map model_id -> unloader_function
        return cls._instance

    def register_model(self, info: ModelInfo, loader: Callable = None, unloader: Callable = None):
        """
        Register a model with the system.
        """
        self._models[info.id] = info
        if loader:
            self._loaders[info.id] = loader
        if unloader:
            self._unloaders[info.id] = unloader
        logger.info(
            f"Registered model: {info.id} ({info.name}) from {info.provider}")

    def list_models(self) -> List[ModelInfo]:
        return list(self._models.values())

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    async def load_model(self, model_id: str):
        if model_id not in self._models:
            raise ValueError(f"Model {model_id} not found")

        loader = self._loaders.get(model_id)
        if loader:
            logger.info(f"Loading model {model_id}...")
            if inspect.iscoroutinefunction(loader):
                await loader()
            else:
                loader()
            self._models[model_id].loaded = True

    async def unload_model(self, model_id: str):
        if model_id not in self._models:
            raise ValueError(f"Model {model_id} not found")

        unloader = self._unloaders.get(model_id)
        if unloader:
            logger.info(f"Unloading model {model_id}...")
            if inspect.iscoroutinefunction(unloader):
                await unloader()
            else:
                unloader()
            self._models[model_id].loaded = False


# Global instance
model_registry = ModelRegistry()
