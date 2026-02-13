
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class LotusKind(str, Enum):
    action = "action"
    feature = "feature"
    provider = "provider"
    resolver = "resolver"
    indexer = "indexer"
    storage = "storage"
    transport = "transport"
    workflow = "workflow"
    nav = "nav"
    config = "config"
    artifact_type = "artifact_type"
    # artifact = "artifact"


class LotusSlot(str, Enum):
    FEATURE_GENERATOR = "feature.generator"
    FEATURE_INGEST = "feature.ingest"
    RESOURCE_ADAPTER = "resource.adapter"
    STORAGE_BLOB = "storage.blob"
    SEARCH_TEXT = "search.text"
    SEARCH_SIMILAR = "search.similar"
    UI_ROUTES_LIST = "ui.routes.list"
    UI_NAVIGATE = "ui.navigate"
    UI_CONFIG_OPEN = "ui.config.open"
    VALUE_STRING = "value.string"
    VALUE_INT = "value.int"
    VALUE_BOOLEAN = "value.boolean"
    WORKFLOW_WAIT = "workflow.wait"
    EVENT_EMIT = "event.emit"
    EVENT_WAIT = "event.wait"
    ARTIFACT_CREATE = "artifact.create"
    ARTIFACT_UPLOAD_INIT = "artifact.upload.init"
    ARTIFACT_UPLOAD_COMPLETE = "artifact.upload.complete"


class LotusIOKind(str, Enum):
    artifact_ref = "artifact_ref"
    artifact_refs = "artifact_refs"
    collection_ref = "collection_ref"
    blob_ref = "blob_ref"
    uri = "uri"
    text = "text"
    number = "number"
    boolean = "boolean"
    json = "json"
    image = "image"
    video = "video"
    audio = "audio"
    embedding = "embedding"


class LotusIOType(BaseModel):
    name: str
    kind: LotusIOKind
    description: Optional[str] = None
    required: bool = False
    array: bool = False
    artifact_type: Optional[str] = None
    json_schema: Optional[Dict[str, Any]] = Field(default=None, alias="schema")

    model_config = {
        "populate_by_name": True,
    }


class LotusUI(BaseModel):
    badge: Optional[str] = None
    icon: Optional[str] = None
    icon_url: Optional[str] = Field(default=None, alias="iconUrl")
    color: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
    }


class LotusAction(BaseModel):
    action: Optional[str] = None
    job_type: Optional[str] = None
    exec: Dict[str, Any] = Field(default_factory=dict)
    expose: Dict[str, Any] = Field(default_factory=dict)
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None

    model_config = {
        "extra": "allow",
    }


class LotusQuery(BaseModel):
    query: Optional[str] = None
    slot: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None

    model_config = {
        "extra": "allow",
    }


class LotusCapability(BaseModel):
    """
    Represents a capability or skill that the Lotus system can utilize.
    """
    id: str
    kind: LotusKind
    title: str
    description: Optional[str] = None

    plugin: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    slot: Optional[str] = None  # e.g., "search.visual.embedding"

    data: Dict[str, Any] = Field(default_factory=dict)

    # Structured input/output hints (optional but preferred)
    inputs: List[LotusIOType] = Field(default_factory=list)
    outputs: List[LotusIOType] = Field(default_factory=list)

    # Capability dependencies
    requires: List[str] = Field(default_factory=list)
    provides: List[str] = Field(default_factory=list)

    # Typed capability payloads (preferred over raw data)
    ui: Optional[LotusUI] = None
    action: Optional[LotusAction] = None
    query: Optional[LotusQuery] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_typed_fields(cls, values):
        if not isinstance(values, dict):
            return values

        data = values.get("data") or {}
        if isinstance(data, dict):
            # Ensure plugin_name/action_name are set from capability plugin field
            plugin_id = values.get("plugin")
            if plugin_id and not data.get("plugin_name") and not data.get("plugin"):
                data["plugin_name"] = plugin_id
            # Normalize: if only "plugin" key, also set "plugin_name"
            if data.get("plugin") and not data.get("plugin_name"):
                data["plugin_name"] = data["plugin"]

            if values.get("ui") is None and data.get("ui") is not None:
                values["ui"] = data.get("ui")

            if values.get("action") is None and any(
                key in data
                for key in ("action", "job_type", "exec", "expose", "input", "output")
            ):
                values["action"] = {
                    "action": data.get("action") or data.get("action_name"),
                    "job_type": data.get("job_type"),
                    "exec": data.get("exec") or {},
                    "expose": data.get("expose") or {},
                    "input": data.get("input"),
                    "output": data.get("output"),
                }

            if values.get("query") is None and data.get("query") is not None:
                values["query"] = {
                    "query": data.get("query"),
                    "slot": data.get("slot"),
                    "input": data.get("input"),
                    "output": data.get("output"),
                }

            values["data"] = data

        return values


class LotusResult(BaseModel):
    capability: LotusCapability
    score: float = 1.0


class LotusQueryResponse(BaseModel):
    query: str
    results: List[LotusResult]
