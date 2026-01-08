from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Since we don't want to depend on FastAPI/Typer directly in Core if possible,
# we use Any for the app/cli objects, or strict types if we add deps.
# For now, let's keep it loose to avoid polluting core with CLI deps.


class PluginIntent(str, Enum):
    REGISTER_API = "register_api"
    REGISTER_CLI = "register_cli"
    REGISTER_CAPABILITY = "register_capability"
    REGISTER_ARTIFACT_TYPE = "register_artifact_type"
    EVENT_LISTENER = "event_listener"


class PluginAction(BaseModel):
    """
    Defines an executable action (usually a CLI command) that the plugin exposes.
    This allows UIs to introspect and run plugin functionality.
    """
    name: str  # Machine readable ID
    label: str  # Human readable label
    description: str = ""
    command_args: str  # The args to pass to 'embeddr' CLI. e.g. "fixtures load"
    requires_confirmation: bool = True
    danger: bool = False  # If true, show red button


class EmbeddrEvent(BaseModel):
    """
    Standard event envelope for inter-plugin communication.
    """
    event_type: str  # e.g. "artifact.created", "embeddings.generated"
    source: str      # plugin name
    payload: Dict[str, Any]
    timestamp: float = 0.0


class EventBus(ABC):
    """
    Interface for the system event bus.
    """
    @abstractmethod
    def publish(self, event: EmbeddrEvent) -> None:
        pass

    @abstractmethod
    def subscribe(self, event_type: str, callback: Any) -> None:
        pass


class PluginContext(BaseModel):
    """
    Context arguments passed to plugin lifecycle methods.
    Contains references to system services.
    """
    bus: Optional[Any] = None  # Using Any to avoid circular imports, typically EventBus
    # We can add db_engine, config, etc here later if needed

    class Config:
        arbitrary_types_allowed = True


class EmbeddrPlugin(ABC):
    """
    Base interface for all Embeddr plugins.
    Plugins must implement this to be loaded by the core.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the plugin, e.g. 'embeddr-umap'"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semver string"""
        pass

    @property
    def intents(self) -> List[PluginIntent]:
        """List of high-level intents this plugin declares."""
        return []

    @property
    def actions(self) -> List[PluginAction]:
        """
        List of executable actions (CLI commands) this plugin exposes.
        """
        return []

    # --- CLI / API Hooks ---

    def register_api(self, router: Any) -> None:
        """
        Called if PluginIntent.REGISTER_API is present.
        'router' is a scoped APIRouter instance prefixed with /api/v1/plugins/{plugin_name}.
        """
        pass

    def register_cli(self, cli_group: Any) -> None:
        """
        Called if PluginIntent.REGISTER_CLI is present.
        'cli_group' is a Typer instance scoped to the plugin name.
        """
        pass

    # --- Core Schema Hooks ---

    def register_types(self) -> List[Dict[str, Any]]:
        """
        Return a list of ArtifactType definitions to register.
        Format:
        [
            {
                "name": "image:comfy",
                "base_type": "image",
                "capabilities": {"edit": True}
            }
        ]
        """
        return []

    def register_capabilities(self) -> List[str]:
        """
        Return a list of capability keys this plugin introduces.
        """
        return []

    # --- Lifecycle ---

    def on_load(self, context: Optional[PluginContext] = None) -> None:
        """Called when plugin is loaded. context provides access to system services."""
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        pass
