
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class LotusResult(BaseModel):
    capability: LotusCapability
    score: float = 1.0


class LotusQueryResponse(BaseModel):
    query: str
    results: List[LotusResult]
