import json
import logging
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlmodel import Session, select

from embeddr_core.models.artifact import Artifact
from embeddr_core.models.artifact_execution import ArtifactExecution
from embeddr_core.models.artifact_lineage import ArtifactLineage, ArtifactLineage
from embeddr_core.models.artifact_annotation import ArtifactAnnotation
from embeddr_core.models.artifact import ArtifactPreview
from embeddr_core.models.artifact_embedding import ArtifactEmbedding
from embeddr_core.models.action_graph import ActionGraph, ActionNode
from embeddr_core.plugin_interface import EmbeddrPlugin, PluginContext, EmbeddrEvent

logger = logging.getLogger("embeddr.core.action_runner")


class ActionRunner:
    """
    Executes ActionArtifact graphs.
    """

    def __init__(self, session: Session, plugin_resolver: Callable[[str], Optional[EmbeddrPlugin]], event_bus: Any = None):
        self.session = session
        self.resolve_plugin = plugin_resolver
        self.bus = event_bus

    def _emit_update(self, execution_id: UUID, node_id: Optional[str] = None, status: str = "running", primary_artifact_id: Optional[UUID] = None):
        if self.bus:
            payload = {
                "id": str(execution_id),
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if node_id:
                payload["node_id"] = node_id
            if primary_artifact_id:
                payload["primary_artifact_id"] = str(primary_artifact_id)

            try:
                event = EmbeddrEvent(
                    event_type="execution_update",
                    source="action_runner",
                    payload=payload
                )
                self.bus.publish(event)
            except Exception as e:
                logger.error(f"Failed to emit execution update: {e}")

    def run_graph(self,
                  graph_artifact_id: UUID,
                  graph: ActionGraph,
                  inputs: Dict[str, Any],
                  parent_execution_id: Optional[UUID] = None,
                  execution_id: Optional[UUID] = None) -> UUID:
        """
        Starts the execution of a graph.
        Creates a primary ArtifactExecution for the workflow run.
        """

        # 1. Create Workflow Execution Record
        if execution_id:
            execution = self.session.get(ArtifactExecution, execution_id)
        else:
            execution = None

        if not execution:
            execution = ArtifactExecution(
                id=execution_id or uuid4(),
                type="workflow.run",
                plugin_name="system",
                status="running",
                priority=10,
                progress=0,
                primary_artifact_id=graph_artifact_id,
                inputs=inputs,
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc)
            )
            self.session.add(execution)
        else:
            # Update existing execution to running
            execution.status = "running"
            execution.started_at = datetime.now(timezone.utc)
            execution.primary_artifact_id = graph_artifact_id
            execution.inputs = inputs
            self.session.add(execution)

        self.session.commit()

        log_ctx = f"[Exec {execution.id}]"
        logger.info(
            f"{log_ctx} Starting workflow execution for graph {graph_artifact_id}")

        try:
            # 2. Resolve Inputs (Inject exposed inputs)
            # This implementation assumes a simple synchronous execution for the POC.
            # Real implementation would be async/queued.

            node_results = {}  # node_id -> {"outputs": {...}}

            # 3. Topological Sort (Simplified: Just iterate until stuck or done)
            # For this POC, we assume the nodes list in the JSON is already sorted or we just
            # find runnable nodes.

            pending_nodes = list(graph.nodes)
            completed_nodes = set()

            while pending_nodes:
                progress = False
                for node in pending_nodes[:]:
                    if self._can_run(node, graph, completed_nodes):
                        self._run_node(node, graph, inputs,
                                       node_results, execution.id)
                        completed_nodes.add(node.id)
                        pending_nodes.remove(node)
                        progress = True

                if not progress and pending_nodes:
                    raise ValueError(
                        f"Graph cycle or missing inputs detected. Pending: {[n.id for n in pending_nodes]}")

            # 4. Finish
            execution.status = "completed"
            execution.finished_at = datetime.now(timezone.utc)
            execution.progress = 100
            execution.outputs = self._collect_workflow_outputs(
                graph, node_results)
            self.session.add(execution)
            self.session.commit()

            return execution.id

        except Exception as e:
            logger.exception(f"{log_ctx} Workflow failed")
            execution.status = "failed"
            execution.error = str(e)
            execution.finished_at = datetime.now(timezone.utc)
            self.session.add(execution)
            self.session.commit()
            raise e

    def _can_run(self, node: ActionNode, graph: ActionGraph, completed_nodes: set) -> bool:
        """Check if all upstream dependencies are met."""
        for input_name, input_def in node.inputs.items():
            if input_def.link:
                if input_def.link.node_id not in completed_nodes:
                    return False
        return True

    def _run_node(self,
                  node: ActionNode,
                  graph: ActionGraph,
                  workflow_inputs: Dict[str, Any],
                  node_results: Dict[str, Any],
                  parent_execution_id: UUID):

        # Resolve Input Values
        node_inputs = {}
        for name, spec in node.inputs.items():
            if spec.exposed:
                # Get from workflow inputs (using node_id.port as key or similar mapping from Interface)
                # For simplicity here: use name if matches, else look in graph.interface
                # The spec says interface maps exposed ports.
                # Let's simple-mapping: if spec.exposed, look in workflow_inputs[name] (naive)
                # Better: assume workflow_inputs passes exposed ports by name defined in Interface
                # We need to look up the Label/Port name in Interface.
                # For this POC, we check workflow_inputs for "node_id.port_name" OR just "port_name"
                val = workflow_inputs.get(
                    name) or workflow_inputs.get(f"{node.id}.{name}")
                node_inputs[name] = val
            elif spec.link:
                # Get from upstream
                source_node = spec.link.node_id
                source_port = spec.link.output_port
                try:
                    val = node_results[source_node]["outputs"][source_port]
                    node_inputs[name] = val
                except KeyError:
                    raise ValueError(
                        f"Missing output {source_port} from node {source_node}")
            else:
                # Static value
                node_inputs[name] = spec.value

        # Execute Plugin
        plugin = self.resolve_plugin(node.plugin)
        if not plugin:
            raise ValueError(f"Plugin {node.plugin} not found")

        # Create Execution Record for NODE
        node_exec = ArtifactExecution(
            id=uuid4(),
            type="action.run",
            plugin_name=node.plugin,
            status="running",
            inputs={
                **node_inputs, "parent_execution_id": str(parent_execution_id), "node_id": node.id},
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc)
        )
        self.session.add(node_exec)
        self.session.commit()

        # Emit Start
        self._emit_update(node_exec.id, node_id=node.id,
                          status="running", primary_artifact_id=parent_execution_id)

        try:
            # CALL PLUGIN EXECUTE
            # Protocol: execute(action, exec_id, inputs) -> outputs dict
            result = plugin.execute(node.action, node_exec.id, node_inputs)

            # Handle Outputs per Protocol
            # defined in spec: produced_artifact_ids, metadata_patches

            self._persist_outputs(result, node_exec)

            # Emit success
            self._emit_update(node_exec.id, node_id=node.id,
                              status="completed", primary_artifact_id=parent_execution_id)

            # Store results for downstream

            # Store results for downstream
            # result usually contains keys matching outputs
            # But the plugin might return { "produced_artifact_ids": [...], "thumbnails": [...] }
            # If the output port is "thumbnails", we expect it in result["thumbnails"] OR
            # we imply "produced_artifact_ids" IS the output for certain types?
            # Creating a unified map of outputs:

            outputs_map = {}
            for out_name in node.outputs.keys():
                if out_name in result:
                    outputs_map[out_name] = result[out_name]
                # Special cases
                elif out_name == "produced_artifacts" and "produced_artifact_ids" in result:
                    outputs_map[out_name] = result["produced_artifact_ids"]

            node_results[node.id] = {"outputs": outputs_map}

            node_exec.status = "completed"
            node_exec.outputs = result  # Store full raw result
            node_exec.finished_at = datetime.now(timezone.utc)
            node_exec.progress = 100
            self.session.add(node_exec)
            self.session.commit()

        except Exception as e:
            node_exec.status = "failed"
            node_exec.error = str(e)
            node_exec.finished_at = datetime.now(timezone.utc)
            self.session.add(node_exec)
            self.session.commit()
            raise e

    def _persist_outputs(self, result: Dict[str, Any], execution: ArtifactExecution):
        """
        Handles the 'Action Execution Protocol' outputs.
        """
        # 1. Produced Artifacts need no special handling if they were created by the plugin
        # BUT ideally the plugin returned IDs and we might verify them or link lineage.

        produced_ids = result.get("produced_artifact_ids", [])

        # Link Lineage: Parent(s) -> Child(ren)
        # We need to know who the parents were.
        # Usually found in inputs['artifact_ids']
        parent_ids = execution.inputs.get("artifact_ids", [])
        if isinstance(parent_ids, str):
            parent_ids = [parent_ids]

        if produced_ids and parent_ids:
            for child_id in produced_ids:
                for parent_id in parent_ids:
                    # check if exists
                    exists = self.session.get(
                        ArtifactLineage, (parent_id, child_id))
                    if not exists:
                        link = ArtifactLineage(
                            parent_id=parent_id,
                            child_id=child_id,
                            relationship_metadata={
                                "execution_id": str(execution.id)},
                            created_at=datetime.now(timezone.utc)
                        )
                        self.session.add(link)

        # 2. Metadata Patches
        # "metadata_patches": [ { "op": "...", "artifact_id": "...", ... } ]
        patches = result.get("metadata_patches", [])
        for patch in patches:
            self._apply_patch(patch)

    def _apply_patch(self, patch: Dict[str, Any]):
        op = patch.get("op")
        aid = patch.get("artifact_id")

        if op == "create_preview":
            # { "op": "create_preview", "artifact_id": "...", "data": { ... } }
            data = patch.get("data", {})
            preview = ArtifactPreview(
                id=uuid4(),
                artifact_id=aid,
                preview_type=data.get("preview_type", "thumbnail"),
                mime_type=data.get("mime_type", "image/webp"),
                uri=data.get("uri"),
                width=data.get("width"),
                height=data.get("height"),
                plugin_name=data.get("plugin_name"),
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(preview)

        elif op == "create_annotation":
            data = patch.get("data", {})
            ann = ArtifactAnnotation(
                id=uuid4(),
                artifact_id=aid,
                text=data.get("text", ""),
                annotation_type=data.get("annotation_type", "general"),
                plugin_name=data.get("plugin_name"),
                confidence=data.get("confidence", 1.0),
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(ann)

        elif op == "create_embedding":
            data = patch.get("data", {})
            emb = ArtifactEmbedding(
                id=uuid4(),
                artifact_id=aid,
                model_name=data.get("model_name"),
                vector_dim=len(data.get("vector")),
                vector_json=data.get("vector"),
                space=data.get("space", "default"),
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(emb)

        # Commit incrementally or at end of node run
        # Here we rely on outer commit

    def _collect_workflow_outputs(self, graph: ActionGraph, node_results: Dict) -> Dict:
        """Map exposed outputs from node results."""
        outputs = {}
        for out_def in graph.interface.exposed_outputs:
            try:
                val = node_results[out_def.node]["outputs"][out_def.port]
                outputs[out_def.label] = val
            except KeyError:
                pass
        return outputs
