from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class NodeInputLink(BaseModel):
    """Refers to an output from another node."""
    node_id: str
    output_port: str


class ActionNodeInput(BaseModel):
    """
    Input configuration for a node.
    Can be a static value, or a link to another node's output.
    """
    type: str  # "string", "int", "artifact_refs", "json"
    value: Optional[Any] = None  # Static value
    link: Optional[NodeInputLink] = None  # Connection from upstream
    exposed: bool = False  # If true, this is a parameter of the graph itself


class ActionNodeOutput(BaseModel):
    """Output definition for a node."""
    type: str  # "artifact_refs", "json", "events"
    accepts: List[str] = []  # e.g. ["image/png", "*"]
    hidden: bool = False


class ActionNode(BaseModel):
    """A single step in the action graph."""
    id: str
    kind: str = "plugin_action"  # "plugin_action", "control_flow", etc.
    plugin: str
    action: str
    inputs: Dict[str, ActionNodeInput] = {}
    outputs: Dict[str, ActionNodeOutput] = {}
    metadata: Dict[str, Any] = {}


class ActionEdge(BaseModel):
    """Connects an output port of one node to an input port of another."""
    from_node: str
    from_port: str
    to_node: str
    to_port: str


class GraphInterfacePort(BaseModel):
    """Exposed input/output for the graph as a whole."""
    node: str
    port: str
    label: str
    type: Optional[str] = None


class ActionGraphInterface(BaseModel):
    exposed_inputs: List[GraphInterfacePort] = []
    exposed_outputs: List[GraphInterfacePort] = []


class ActionGraph(BaseModel):
    """
    The JSON structure stored in Artifact.metadata_json['graph'] for type='action:graph'.
    """
    version: int = 1
    nodes: List[ActionNode] = []
    edges: List[ActionEdge] = []
    interface: ActionGraphInterface = Field(
        default_factory=ActionGraphInterface)
