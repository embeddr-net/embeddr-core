from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Literal, Optional
from embeddr_core.models.lotus import LotusCapability
from embeddr_core.models.artifact_type import ArtifactTypeSpec
from pydantic import BaseModel
from .models.analysis_capability import AnalysisCapability

# Since we don't want to depend on FastAPI/Typer directly in Core if possible,
# we use Any for the app/cli objects, or strict types if we add deps.
# For now, let's keep it loose to avoid polluting core with CLI deps.


class PluginIntent(str, Enum):
    REGISTER_API = "register_api"
    REGISTER_CLI = "register_cli"
    REGISTER_CAPABILITY = "register_capability"
    REGISTER_ARTIFACT_TYPE = "register_artifact_type"
    ZEN_PANEL = "zen_panel"
    DATABASE_ACCESS = "database_access"
    EXECUTION_HANDLER = "execution_handler"  # Used for back-channel executions
    DRAG_DROP_TARGET = "drag_drop_target"
    EVENT_LISTENER = "event_listener"
    # Lotus-native intent markers
    REGISTER_LOTUS = "register_lotus"
    PROVIDE_SEARCH = "provide_search"
    PROVIDE_INDEXER = "provide_indexer"
    PROVIDE_STORAGE = "provide_storage"

    # Deprecated: prefer Lotus capabilities instead of intent-specific logic
    PROVIDE_EMBEDDINGS = "provide_embeddings"
    PROVIDE_MODEL_INSIGHTS = "provide_model_insights"
    REGISTER_MCP_TOOL = "register_mcp_tool"
    REGISTER_MCP_RESOURCE = "register_mcp_resource"
    AUTO_ANALYSIS = "auto_analysis"


class PluginAction(BaseModel):
    """
    Defines an executable action (usually a CLI command) that the plugin exposes.
    This allows UIs to introspect and run plugin functionality.
    """
    name: str  # Machine readable ID (required)
    label: str  # Human readable label (required)
    description: str = ""

    # CLI Command (legacy/simple)
    # The args to pass to 'embeddr' CLI. e.g. "fixtures load"
    command_args: Optional[str] = None

    requires_confirmation: bool = True
    danger: bool = False  # If true, show red button

    # Execution Framework
    tier: str = "user"  # user, system
    inputs: List[str] = []  # Capabilities/Types e.g. ["artifact:image"]
    outputs: List[str] = []
    idempotent: bool = False

    # UI Components Registration (Optional if action is CLI-only)
    # The name of the exported component class in the JS bundle
    ui_component: Optional[str] = None
    # e.g. "zen-overlay", "sidebar", "editor"
    ui_location: Optional[str] = None

    # Action Graph Integration
    # The job identifier if this is a programmable action
    job_type: Optional[str] = None
    # JSON Schema for the payload input
    payload_schema: Optional[Dict[str, Any]] = None


class FrontendComponent(BaseModel):
    """
    Defines a standalone UI component provided by the plugin.
    Unlike actions, these are mounted automatically by the frontend.
    Deprecated in favor of explicit panel/page/widget registrations.
    """
    name: str  # Unique ID within plugin
    component: str  # Name of exported component in bundle
    location: str  # "zen-toolbox-tab", "sidebar", "header", etc.
    label: Optional[str] = None
    icon: Optional[str] = None  # Lucide icon name string
    props: Dict[str, Any] = {}


class PanelComponent(BaseModel):
    """
    A Zen UI panel component (draggable, chromed by the Zen shell).
    """
    name: str
    component: str
    label: Optional[str] = None
    icon: Optional[str] = None
    props: Dict[str, Any] = {}


class PageComponent(BaseModel):
    """
    A routed page component, mounted on its own route.
    """
    name: str
    component: str
    route: str
    label: Optional[str] = None
    icon: Optional[str] = None
    props: Dict[str, Any] = {}


class WidgetComponent(BaseModel):
    """
    A command-bar widget (compact UI surface, e.g. clock, counter, action chip).
    """
    name: str
    component: str
    label: Optional[str] = None
    icon: Optional[str] = None
    slot: Optional[str] = None  # Optional placement hint for command bar
    props: Dict[str, Any] = {}


class FrontendAction(BaseModel):
    """
    A UI action rendered by the frontend (e.g. toolbox accordion items).
    If component is provided, UI renders it inline (accordion).
    If not, UI treats it as a button and calls handler (future) or triggers a server action.
    """
    name: str                 # unique ID within plugin
    label: str
    description: str = ""

    # Name of exported React component in the plugin's JS bundle
    component: Optional[str] = None

    # Where in the UI it should appear (matches your getActions keys)
    location: str = "zen-toolbox-action"  # e.g. "zen-toolbox-action"

    # Lucide icon name (string) so frontend can map it
    icon: Optional[str] = None

    danger: bool = False
    requires_confirmation: bool = False

    # Optional props passed to component
    props: Dict[str, Any] = {}


class EmbeddrEvent(BaseModel):
    """
    Standard event envelope for inter-plugin communication.
    """
    event_type: str  # e.g. "artifact.created", "embeddings.generated"
    source: str      # plugin name
    payload: Dict[str, Any]
    timestamp: float = 0.0


ToastVariant = Literal["default", "success", "error", "destructive"]


@dataclass
class UIHandle:
    bus: Any

    def toast(
        self,
        title: str,
        description: str = "",
        variant: ToastVariant = "default",
        *,
        source: str = "plugin",
        id: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "variant": variant,
        }
        if id:
            payload["id"] = id
        self.bus.emit("ui:toast", payload, source=source)

    def navigate(self, route: str, *, source: str = "plugin") -> None:
        self.bus.emit("ui:navigate", {"route": route}, source=source)

    def open_artifact(self, artifact_id: str, *, source: str = "plugin") -> None:
        self.bus.emit("ui:open_artifact", {
                      "artifact_id": artifact_id}, source=source)


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
    # Use Dict[str, Any] for maximum compatibility
    capability_registry: Optional[Dict[str, Any]] = None
    resources: Optional[Any] = None  # Typically ResourceManager
    # We can add db_engine, config, etc here later if needed

    @property
    def ui(self) -> UIHandle:
        return UIHandle(self.bus)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow"  # Allow extra fields to avoid AttributeError during migrations
    }


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

    @property
    def analysis_capabilities(self) -> List[AnalysisCapability]:
        """
        List of auto-analysis capabilities this plugin provides.
        Only used if intent includes AUTO_ANALYSIS.
        """
        return []

    @property
    def frontend_components(self) -> List[FrontendComponent]:
        """
        List of frontend components this plugin provides.
        Deprecated: prefer panels/pages/widgets.
        """
        return []

    @property
    def panels(self) -> List[PanelComponent]:
        """
        Zen UI panels provided by this plugin.
        """
        return []

    @property
    def pages(self) -> List[PageComponent]:
        """
        Routed pages provided by this plugin.
        """
        return []

    @property
    def widgets(self) -> List[WidgetComponent]:
        """
        Command-bar widgets provided by this plugin.
        """
        return []

    @property
    def frontend_actions(self) -> List[FrontendAction]:
        """
        List of frontend actions (e.g. toolbox items) this plugin provides.
        """
        return []

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return a JSON schema or a list of config items the plugin uses.
        """
        return {}

    def get_config(self) -> Dict[str, Any]:
        """
        Return the current configuration values.
        """
        return {}

    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update the plugin's configuration.
        """
        pass

    # --- Lifecycle Hooks ---

    def on_load(self, context: Optional[PluginContext] = None) -> None:
        """Called when plugin is loaded. context provides access to system services."""
        pass

    def on_startup(self, context: Optional[PluginContext] = None) -> None:
        """
        Called when the application is fully started (after DB and servers are up).
        Use this to register dynamic capabilities, start background threads, etc.
        """
        pass

    def on_shutdown(self, context: Optional[PluginContext] = None) -> None:
        """
        Called when the application is shutting down.
        Use this for cleanup, closing connections, etc.
        """
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        pass

    # --- CLI / API Hooks ---

    def register_api(self, api: Any) -> None:
        """
        Called if PluginIntent.REGISTER_API is present.
        'api' is a scoped APIRouter instance prefixed with /api/v1/plugins/{plugin_name}.
        """
        pass

    def register_cli(self, cli: Any) -> None:
        """
        Called if PluginIntent.REGISTER_CLI is present.
        'cli' is a Typer instance scoped to the plugin name.
        """
        pass

    # --- MCP Hooks ---

    def register_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Return list of MCP tool definitions.
        Format should match MCP Tool schema.
        {
            "name": "tool_name",
            "description": "...",
            "inputSchema": {...},
            "handler": callable_function
        }
        """
        return []

    def register_mcp_resources(self) -> List[Dict[str, Any]]:
        """
        Return list of MCP resource definitions.
        """
        return []

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

    def provided_artifact_types(self) -> List[ArtifactTypeSpec]:
        """
        Return declarative artifact types for core reconciliation.
        Prefer this over register_types for schema contributions.
        """
        return []

    def execute(self, action_name: str, execution_id: Any, inputs: Dict[str, Any], context: Optional[PluginContext] = None) -> Dict[str, Any]:
        """
        Execute an action defined by this plugin.
        Should raise exception on failure.
        Return value is stored as 'outputs'.
        """
        raise NotImplementedError(
            f"Plugin {self.name} does not support execution of {action_name}")

    def register_capabilities(self) -> List[str]:
        """
        Return a list of capability keys this plugin introduces.
        """
        return []

    # --- LOTUS HOOKS --- #

    def register_lotus(self) -> list[LotusCapability]:
        """
        Register Lotus capabilities provided by this plugin.
        """
        return []

    # --- Deprecated Hooks (kept for backward compat if any) ---

    def load(self, context=None):
        """Deprecated: Use on_load instead."""
        self.on_load(context)


class SimplePlugin(EmbeddrPlugin):
    """
    Convenience base class for plugins that only need a static name/version.
    Set PLUGIN_NAME and PLUGIN_VERSION on the subclass and you can omit
    explicit name/version properties.
    """

    PLUGIN_NAME: str = ""
    PLUGIN_VERSION: str = ""

    @property
    def name(self) -> str:
        if not self.PLUGIN_NAME:
            raise ValueError("PLUGIN_NAME must be set on SimplePlugin")
        return self.PLUGIN_NAME

    @property
    def version(self) -> str:
        if not self.PLUGIN_VERSION:
            raise ValueError("PLUGIN_VERSION must be set on SimplePlugin")
        return self.PLUGIN_VERSION


class LotusPlugin(SimplePlugin):
    """
    Brand-aligned alias for SimplePlugin.
    """

    pass
