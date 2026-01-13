import logging
import os
import time
from typing import List
from uuid import UUID
from datetime import datetime

from sqlmodel import Session, select, col

from embeddr_core.models.artifact import Artifact, ArtifactPreview
from embeddr_core.models.artifact_embedding import ArtifactEmbedding
from embeddr_core.models.artifact_annotation import ArtifactAnnotation
from embeddr_core.services import embedding
# Note: We need to inject the VectorStoreService instance or access a global ONE.
# For now, let's assume we can import a getter or instantiation logic
# from embeddr_core.services.vector_store import get_vector_service

logger = logging.getLogger(__name__)


def generate_embeddings_for_artifacts(
    session: Session,
    model_name: str = "openai/clip-vit-base-patch32",
    batch_size: int = 8,
    stop_event=None,
    progress_callback=None,
    force_recompute: bool = False,
    artifact_ids: List[str] = None,
    plugin_name: str = "core:clip"
):
    """
    Generates embeddings for all artifacts that support it and don't have them.
    If artifact_ids is provided, only processes those artifacts.
    """
    # 1. Find candidates: Type 'image' or capability 'embeddable:vision' (TODO: capability check)
    # For now, simplistic check on type_name
    query = select(Artifact).where(
        col(Artifact.type_name).in_(["image", "image:comfy", "text", "document"]))

    # Optional filter by IDs
    if artifact_ids:
        # Convert strings to UUIDs for the query
        uuids = []
        for aid in artifact_ids:
            try:
                uuids.append(UUID(aid) if isinstance(aid, str) else aid)
            except ValueError:
                pass
        if uuids:
            query = query.where(col(Artifact.id).in_(uuids))

    # 2. Filter out those that already have embeddings for this model
    # (Unless force_recompute is True)
    if not force_recompute:
        from sqlalchemy import exists, and_
        # Use NOT EXISTS for better performance than NOT IN with subquery
        has_embedding = exists().where(
            and_(
                ArtifactEmbedding.artifact_id == Artifact.id,
                ArtifactEmbedding.model_name == model_name
            )
        )
        query = query.where(~has_embedding)

    start_scan = time.time()
    artifacts_to_process = session.exec(query).all()
    scan_duration = time.time() - start_scan

    total_count = len(artifacts_to_process)

    logger.info(
        f"Found {total_count} artifacts needing embeddings for {model_name} (Scan took {scan_duration:.2f}s)")

    if progress_callback:
        progress_callback(0, total_count, "Starting generation...")

    # Process in batches
    current_batch = []
    current_batch_bytes = []
    processed = 0

    for artifact in artifacts_to_process:
        if stop_event and stop_event.is_set():
            break

        # Handle text/docs separately
        if artifact.type_name in ["text", "document"]:
            # Try to find content annotation first
            content_annotation = session.exec(select(ArtifactAnnotation).where(
                ArtifactAnnotation.artifact_id == artifact.id,
                ArtifactAnnotation.annotation_type == "content"
            )).first()

            text_content = ""
            if content_annotation:
                text_content = content_annotation.text
            elif artifact.metadata_json and isinstance(artifact.metadata_json, dict) and artifact.metadata_json.get("text_content"):
                text_content = artifact.metadata_json["text_content"]
            elif artifact.uri and os.path.exists(artifact.uri):
                # Fallback to reading file if readable
                try:
                    with open(artifact.uri, "r", encoding="utf-8", errors="ignore") as f:
                        text_content = f.read()
                        # Limit text size for now
                        text_content = text_content[:2000]
                except:
                    pass

            if text_content:
                try:
                    emb = embedding.get_text_embedding(
                        text_content, model_name=model_name)
                    _save_embedding(session, artifact.id, emb,
                                    model_name, space="textual", plugin_name=plugin_name)
                    processed += 1
                    # Periodic commit for text artifacts
                    if processed % 20 == 0:
                        session.commit()
                except Exception as e:
                    logger.error(
                        f"Failed to embed text artifact {artifact.id}: {e}")
            continue

        # Resolve path - prioritizing thumbnails for vision if available
        # This MASSIVELY speeds up embedding generation for large raw files/images

        # Handle file:// prefix
        fpath = artifact.uri
        if fpath and fpath.startswith("file://"):
            fpath = fpath[7:]

        # If it's an image, check for a thumbnail preview
        if artifact.type_name in ["image", "image:comfy"]:
            preview = session.exec(
                select(ArtifactPreview)
                .where(ArtifactPreview.artifact_id == artifact.id)
                .where(ArtifactPreview.preview_type == "thumbnail")
                .order_by(ArtifactPreview.created_at.desc())
            ).first()

            # Check thumbnail path
            if preview and preview.uri:
                thumb_path = preview.uri
                if thumb_path.startswith("file://"):
                    thumb_path = thumb_path[7:]

                if os.path.exists(thumb_path):
                    fpath = thumb_path

        if not fpath or not os.path.exists(fpath):
            continue

        try:
            with open(fpath, "rb") as f:
                content = f.read()

            current_batch.append(artifact)
            current_batch_bytes.append(content)
        except Exception as e:
            logger.error(f"Error reading {fpath}: {e}")
            continue

        if len(current_batch) >= batch_size:
            if progress_callback:
                first_item_name = os.path.basename(
                    current_batch[0].uri) if current_batch[0].uri else "unknown"
                progress_callback(
                    processed, total_count, f"Processing batch {processed // batch_size + 1} ({len(current_batch)} items). First: {first_item_name}...")

            start_ts = time.time()
            _process_batch(session, current_batch,
                           current_batch_bytes, model_name, plugin_name=plugin_name)
            duration = time.time() - start_ts

            processed += len(current_batch)
            if progress_callback:
                rate = len(current_batch) / duration if duration > 0 else 0
                progress_callback(processed, total_count,
                                  f"Processed {processed}/{total_count} - Batch took {duration:.2f}s ({rate:.2f} it/s)")

            # Reset
            current_batch = []
            current_batch_bytes = []

    # Final batch
    if current_batch:
        _process_batch(session, current_batch,
                       current_batch_bytes, model_name, plugin_name=plugin_name)

    session.commit()
    logger.info("Embedding generation complete.")


def _save_embedding(session, artifact_id, vec, model_name, space="visual", plugin_name="core:clip"):
    """Helper to save a single embedding"""
    try:
        # Check for existing to deduplicate (and clean up duplicates)
        existing = session.exec(
            select(ArtifactEmbedding).where(
                ArtifactEmbedding.artifact_id == artifact_id,
                ArtifactEmbedding.model_name == model_name,
                ArtifactEmbedding.plugin_name == plugin_name
            )
        ).all()

        if existing:
            # Update first, delete others
            target = existing[0]
            target.vector_json = vec.tolist() if hasattr(vec, 'tolist') else list(vec)
            target.vector_dim = len(vec)
            target.space = space
            target.created_at = datetime.utcnow()
            session.add(target)

            for extra in existing[1:]:
                session.delete(extra)
        else:
            emb = ArtifactEmbedding(
                artifact_id=artifact_id,
                model_name=model_name,
                vector_dim=len(vec),
                vector_json=vec.tolist() if hasattr(vec, 'tolist') else list(vec),
                space=space,
                plugin_name=plugin_name
            )
            session.add(emb)
    except Exception as e:
        logger.error(f"Failed to save embedding for {artifact_id}: {e}")


def _process_batch(session, artifacts: List[Artifact], images_bytes: List[bytes], model_name: str, plugin_name: str = "core:clip"):
    try:
        vectors = embedding.get_image_embeddings_batch(
            images_bytes, model_name)

        for i, vec in enumerate(vectors):
            if vec is not None:
                art = artifacts[i]

                # Deduplicate and cleanup
                existing = session.exec(
                    select(ArtifactEmbedding).where(
                        ArtifactEmbedding.artifact_id == art.id,
                        ArtifactEmbedding.model_name == model_name,
                        ArtifactEmbedding.plugin_name == plugin_name
                    )
                ).all()

                if existing:
                    target = existing[0]
                    target.vector_json = vec.tolist()
                    target.vector_dim = len(vec)
                    # Use existing space if set, or force? Default to current logic
                    # target.created_at = datetime.utcnow() # Optional update
                    session.add(target)
                    for extra in existing[1:]:
                        session.delete(extra)
                else:
                    emb = ArtifactEmbedding(
                        artifact_id=art.id,
                        model_name=model_name,
                        vector_dim=len(vec),
                        vector_json=vec.tolist(),
                        space="visual",
                        plugin_name=plugin_name
                    )
                    session.add(emb)

        session.commit()
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        session.rollback()
