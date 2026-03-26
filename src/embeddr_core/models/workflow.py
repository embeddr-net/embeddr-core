from typing import Dict, List, Optional, Literal, Any, Union
from pydantic import BaseModel, Field

# Exposure Flags (Bitmask)
# 1 = UI, 2 = API, 4 = MCP
EXPOSURE_INTERNAL = 0
EXPOSURE_UI = 1
EXPOSURE_API = 2
EXPOSURE_MCP = 4
# Legacy string support is deprecated but kept for compatibility handling
ExposureLevel = Union[int, Literal["internal", "ui", "api", "mcp"]]


class WorkflowPort(BaseModel):
    """Defines a single input or output on a workflow."""
    name: str = Field(description="Unique identifier for this port")
    type: str = Field(
        description="Data type (e.g. 'image', 'string', 'number', 'artifact')")
    description: Optional[str] = None
    default: Optional[Any] = Field(
        default=None, description="Default value if not provided")
    exposure: ExposureLevel = Field(
        default=EXPOSURE_INTERNAL, description="Visibility level (bitmask)")

    # UI hints
    group: Optional[str] = None
    widget: Optional[str] = None  # e.g. "slider", "file_upload"
    options: Optional[List[Any]] = None  # For enums


class LotusPort(BaseModel):
    """Workflow-facing port definition used by Lotus specs."""
    name: str = Field(description="Unique identifier for this port")
    type: str = Field(description="Data type (e.g. 'image', 'text', 'number')")
    description: Optional[str] = None
    default: Optional[Any] = Field(default=None)
    exposure: ExposureLevel = Field(
        default=EXPOSURE_INTERNAL, description="Visibility level (bitmask)")
    group: Optional[str] = None
    widget: Optional[str] = None
    options: Optional[List[Any]] = None


class WorkflowImplementation(BaseModel):
    """The opaque payload for the plugin to execute."""
    type: str = Field(description="Engine type e.g. 'comfyui-graph'")
    version: Optional[str] = None
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="The raw graph or script config")


class WorkflowStep(BaseModel):
    """Single step in a workflow spec."""
    id: str = Field(description="Step identifier")
    action_ref: str = Field(description="Action/capability id")
    defaults: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Optional[Dict[str, Any]] = None


class WorkflowEdge(BaseModel):
    """Edge connecting step ports or workflow ports."""
    from_ref: str = Field(
        description="source ref (step.port or workflow.in.port)")
    to_ref: str = Field(
        description="target ref (step.port or workflow.out.port)")


class WorkflowSpec(BaseModel):
    """Lotus workflow definition (control plane)."""
    id: str
    name: str
    version: str = "1.0"
    ports_in: Dict[str, LotusPort] = Field(default_factory=dict)
    ports_out: Dict[str, LotusPort] = Field(default_factory=dict)
    steps: List[WorkflowStep] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)


class WorkflowPreset(BaseModel):
    """Named preset for a workflow spec."""
    id: str
    workflow_id: str
    name: str
    description: Optional[str] = None
    defaults: Dict[str, Any] = Field(default_factory=dict)


class WorkflowArtifactMetadata(BaseModel):
    """
    The structured content stored in Artifact.metadata_json for type="workflow".
    """
    schema_version: str = "1.0"
    inputs: Dict[str, WorkflowPort] = {}
    outputs: Dict[str, WorkflowPort] = {}
    side_effects: List[str] = []  # e.g. ["filesystem.write", "gpu.compute"]
    implementation: WorkflowImplementation
