import logging
import os
from typing import List
from uuid import UUID

from sqlmodel import Session, select, col

from embeddr_core.models.artifact import Artifact
from embeddr_core.models.artifact_embedding import ArtifactEmbedding
from embeddr_core.services.embedding import get_image_embeddings_batch
# Note: We need to inject the VectorStoreService instance or access a global ONE.
# For now, let's assume we can import a getter or instantiation logic
# from embeddr_core.services.vector_store import get_vector_service

logger = logging.getLogger(__name__)


def generate_embeddings_for_artifacts(
    session: Session,
    model_name: str = "openai/clip-vit-base-patch32",
    batch_size: int = 10,
    stop_event=None,
    progress_callback=None,
    force_recompute: bool = False
):
    """
    Generates embeddings for all artifacts that support it and don't have them.
    """
    # 1. Find candidates: Type 'image' or capability 'embeddable:vision' (TODO: capability check)
    # For now, simplistic check on type_name
    query = select(Artifact).where(
        col(Artifact.type_name).in_(["image", "image:comfy"]))

    # 2. Filter out those that already have embeddings for this model
    # (Unless force_recompute is True)
    if not force_recompute:
        # Subquery to find IDs with existing embeddings
        existing_sub = select(ArtifactEmbedding.artifact_id)\
            .where(ArtifactEmbedding.model_name == model_name)

        query = query.where(col(Artifact.id).not_in(existing_sub))

    artifacts_to_process = session.exec(query).all()
    total_count = len(artifacts_to_process)

    logger.info(
        f"Found {total_count} artifacts needing embeddings for {model_name}")

    if progress_callback:
        progress_callback(0, total_count, "Starting generation...")

    # Process in batches
    current_batch = []
    current_batch_bytes = []
    processed = 0

    for artifact in artifacts_to_process:
        if stop_event and stop_event.is_set():
            break

        # Resolve path - Assuming URI is file path for now
        # TODO: Handle non-file URIs via an AssetManager or similar
        fpath = artifact.uri
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
            _process_batch(session, current_batch,
                           current_batch_bytes, model_name)
            processed += len(current_batch)
            if progress_callback:
                progress_callback(processed, total_count,
                                  f"Processed {processed}/{total_count}")

            # Reset
            current_batch = []
            current_batch_bytes = []

    # Final batch
    if current_batch:
        _process_batch(session, current_batch, current_batch_bytes, model_name)

    logger.info("Embedding generation complete.")


def _process_batch(session, artifacts: List[Artifact], images_bytes: List[bytes], model_name: str):
    try:
        vectors = get_image_embeddings_batch(images_bytes, model_name)

        for i, vec in enumerate(vectors):
            if vec is not None:
                art = artifacts[i]

                # Check existance manually if we didn't filter earlier, but we did.
                # Just insert.
                emb = ArtifactEmbedding(
                    artifact_id=art.id,
                    model_name=model_name,
                    vector_dim=len(vec),
                    vector_json=vec.tolist(),  # explicit convert to list for JSON field
                    space="visual",  # Hardcoded for now, CLIP is visual
                    plugin_name="core:clip"
                )
                session.add(emb)

        session.commit()
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        session.rollback()
