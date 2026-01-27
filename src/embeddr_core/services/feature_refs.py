from __future__ import annotations

from typing import Optional, Dict, Any
from uuid import UUID
from sqlmodel import Session, select

from embeddr_core.models.artifact_feature import ArtifactFeatureRef


def build_feature_name(model_name: Optional[str], space: Optional[str]) -> str:
    if model_name and space:
        return f"{model_name}:{space}"
    if model_name:
        return model_name
    if space:
        return f"feature:{space}"
    return "feature"


def upsert_feature_ref(
    session: Session,
    artifact_id: UUID,
    feature_type: str,
    name: str,
    storage_kind: str,
    storage_ref: Dict[str, Any],
    producer_plugin: Optional[str] = None,
    producer_version: Optional[str] = None,
    model_name: Optional[str] = None,
    space: Optional[str] = None,
    vector_dim: Optional[int] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
    content_hash: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> ArtifactFeatureRef:
    existing = session.exec(
        select(ArtifactFeatureRef).where(
            ArtifactFeatureRef.artifact_id == artifact_id,
            ArtifactFeatureRef.feature_type == feature_type,
            ArtifactFeatureRef.name == name,
            ArtifactFeatureRef.producer_plugin == producer_plugin,
        )
    ).first()

    if existing:
        existing.storage_kind = storage_kind
        existing.storage_ref = storage_ref
        existing.producer_version = producer_version
        existing.model_name = model_name
        existing.space = space
        existing.vector_dim = vector_dim
        existing.content_hash = content_hash
        existing.schema_version = schema_version
        if metadata_json is not None:
            existing.metadata_json = metadata_json
        session.add(existing)
        return existing

    feature = ArtifactFeatureRef(
        artifact_id=artifact_id,
        feature_type=feature_type,
        name=name,
        producer_plugin=producer_plugin,
        producer_version=producer_version,
        storage_kind=storage_kind,
        storage_ref=storage_ref,
        model_name=model_name,
        space=space,
        vector_dim=vector_dim,
        content_hash=content_hash,
        schema_version=schema_version,
        metadata_json=metadata_json or {},
    )
    session.add(feature)
    return feature
