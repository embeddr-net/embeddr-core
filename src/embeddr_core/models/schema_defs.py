from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Tuple

CORE_SCHEMA_DEFS: Dict[str, Dict[str, Any]] = {
    "ArtifactId": {
        "type": "string",
        "format": "uuid",
        "title": "ArtifactId",
        "description": "UUID of an artifact.",
    },
    "CollectionId": {
        "type": "string",
        "format": "uuid",
        "title": "CollectionId",
        "description": "UUID of a collection.",
    },
    "WorkflowId": {
        "type": "string",
        "format": "uuid",
        "title": "WorkflowId",
        "description": "UUID of a workflow.",
    },
    "ExecutionId": {
        "type": "string",
        "format": "uuid",
        "title": "ExecutionId",
        "description": "UUID of an execution.",
    },
    "GenerationId": {
        "type": "string",
        "format": "uuid",
        "title": "GenerationId",
        "description": "UUID of a generation.",
    },
    "DatasetId": {
        "type": "string",
        "format": "uuid",
        "title": "DatasetId",
        "description": "UUID of a dataset.",
    },
    "SessionId": {
        "type": "string",
        "title": "SessionId",
        "description": "Session identifier.",
    },
    "PluginName": {
        "type": "string",
        "title": "PluginName",
        "description": "Plugin identifier.",
    },
    "ModelName": {
        "type": "string",
        "title": "ModelName",
        "description": "Model identifier.",
    },
    "EmbeddingSpace": {
        "type": "string",
        "title": "EmbeddingSpace",
        "description": "Embedding space identifier.",
    },
    "Uri": {
        "type": "string",
        "format": "uri",
        "title": "Uri",
        "description": "Resource URI.",
    },
    "ArtifactRef": {
        "type": "object",
        "title": "ArtifactRef",
        "description": "Reference to an artifact with optional URLs.",
        "properties": {
            "artifact_id": {"$ref": "#/$defs/ArtifactId"},
            "type_name": {"type": "string"},
            "content_url": {"$ref": "#/$defs/Uri"},
            "preview_url": {"$ref": "#/$defs/Uri"},
        },
        "required": ["artifact_id"],
    },
    "ResourceRef": {
        "type": "object",
        "title": "ResourceRef",
        "description": "Reference to a resource or artifact.",
        "properties": {
            "artifact_id": {"$ref": "#/$defs/ArtifactId"},
            "url": {"$ref": "#/$defs/Uri"},
            "hint_type": {"type": "string"},
        },
    },
}

CORE_FIELD_REFS: Dict[str, Tuple[str, bool]] = {
    "artifact_id": ("ArtifactId", False),
    "artifactId": ("ArtifactId", False),
    "artifact_ids": ("ArtifactId", True),
    "artifactIds": ("ArtifactId", True),
    "collection_id": ("CollectionId", False),
    "collectionId": ("CollectionId", False),
    "collection_ids": ("CollectionId", True),
    "collectionIds": ("CollectionId", True),
    "workflow_id": ("WorkflowId", False),
    "workflowId": ("WorkflowId", False),
    "workflow_ids": ("WorkflowId", True),
    "workflowIds": ("WorkflowId", True),
    "execution_id": ("ExecutionId", False),
    "executionId": ("ExecutionId", False),
    "generation_id": ("GenerationId", False),
    "generationId": ("GenerationId", False),
    "dataset_id": ("DatasetId", False),
    "datasetId": ("DatasetId", False),
    "session_id": ("SessionId", False),
    "sessionId": ("SessionId", False),
    "plugin_name": ("PluginName", False),
    "pluginName": ("PluginName", False),
    "model": ("ModelName", False),
    "model_name": ("ModelName", False),
    "modelName": ("ModelName", False),
    "space": ("EmbeddingSpace", False),
    "spaces": ("EmbeddingSpace", True),
    "resource_ref": ("ResourceRef", False),
    "artifact_ref": ("ArtifactRef", False),
}


def _schema_allows_null(schema: Dict[str, Any]) -> bool:
    schema_type = schema.get("type")
    if isinstance(schema_type, list) and "null" in schema_type:
        return True
    for key in ("anyOf", "oneOf"):
        for option in schema.get(key) or []:
            if _schema_allows_null(option):
                return True
    return False


def _ref_schema(def_name: str, is_array: bool, optional: bool) -> Dict[str, Any]:
    ref = {"$ref": f"#/$defs/{def_name}"}
    if is_array:
        ref = {"type": "array", "items": ref}
    if optional:
        return {"anyOf": [ref, {"type": "null"}]}
    return ref


def _normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(schema, dict):
        return schema

    schema_type = schema.get("type")

    if schema_type == "object" or schema.get("properties"):
        properties = schema.get("properties") or {}
        normalized_props: Dict[str, Any] = {}
        for key, prop_schema in properties.items():
            if key in CORE_FIELD_REFS:
                def_name, is_array = CORE_FIELD_REFS[key]
                optional = _schema_allows_null(prop_schema or {})
                normalized_props[key] = _ref_schema(
                    def_name, is_array, optional)
            else:
                normalized_props[key] = _normalize_schema(prop_schema or {})
        schema["properties"] = normalized_props
        return schema

    if schema_type == "array":
        items = schema.get("items") or {}
        schema["items"] = _normalize_schema(items)
        return schema

    if schema.get("anyOf") or schema.get("oneOf") or schema.get("allOf"):
        for key in ("anyOf", "oneOf", "allOf"):
            if key in schema:
                schema[key] = [
                    _normalize_schema(item or {}) for item in (schema.get(key) or [])
                ]
        return schema

    return schema


def normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(schema)
    normalized = _normalize_schema(normalized)

    defs = normalized.get("$defs") or normalized.get("definitions") or {}
    merged_defs = {**CORE_SCHEMA_DEFS, **defs}
    normalized["$defs"] = merged_defs
    normalized.pop("definitions", None)

    return normalized
