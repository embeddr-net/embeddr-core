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


class WorkflowImplementation(BaseModel):
    """The opaque payload for the plugin to execute."""
    type: str = Field(description="Engine type e.g. 'comfyui-graph'")
    version: Optional[str] = None
    payload: Dict[str, Any] = Field(
        default={}, description="The raw graph or script config")


class WorkflowArtifactMetadata(BaseModel):
    """
    The structured content stored in Artifact.metadata_json for type="workflow".
    """
    schema_version: str = "1.0"
    inputs: Dict[str, WorkflowPort] = {}
    outputs: Dict[str, WorkflowPort] = {}
    side_effects: List[str] = []  # e.g. ["filesystem.write", "gpu.compute"]
    implementation: WorkflowImplementation
