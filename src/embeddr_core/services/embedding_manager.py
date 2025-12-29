import logging
import os

from sqlmodel import Session, select

from embeddr_core.models.library import LocalImage
from embeddr_core.services.embedding import (
    get_image_embeddings_batch,
)
from embeddr_core.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def generate_embeddings_for_library(
    session: Session,
    library_id: int,
    model_name: str = "openai/clip-vit-base-patch32",
    batch_size: int = 10,
    stop_event=None,
    progress_callback=None,
) -> int:
    """
    Generates embeddings for all images in a library that don't have them yet.
    """
    images = session.exec(
        select(LocalImage).where(LocalImage.library_path_id == library_id)
    ).all()

    store = get_vector_store(model_name)
    count = 0

    # Collect images that need embeddings
    images_to_process = []
    for image in images:
        if store.get_vector_by_id(image.id) is None:
            images_to_process.append(image)

    total_images = len(images_to_process)
    logger.info(
        f"Found {total_images} images needing embeddings for library {library_id} using model {model_name}"
    )

    if progress_callback:
        progress_callback(
            0,
            total_images,
            f"Starting embedding generation for {total_images} images...",
        )

    # Process in batches
    BATCH_SIZE = batch_size

    batch_images = []
    batch_image_bytes = []

    for i, image in enumerate(images_to_process):
        # Check for stop signal
        if stop_event and stop_event.is_set():
            logger.info("Embedding generation stopped by user.")
            break

        try:
            if not os.path.exists(image.path):
                continue

            with open(image.path, "rb") as f:
                ib = f.read()

            batch_images.append(image)
            batch_image_bytes.append(ib)

            if len(batch_images) >= BATCH_SIZE:
                # Process batch
                vectors = get_image_embeddings_batch(batch_image_bytes, model_name)

                valid_ids = []
                valid_vectors = []
                valid_metas = []

                for idx, vec in enumerate(vectors):
                    if vec is not None:
                        img = batch_images[idx]
                        valid_ids.append(img.id)
                        valid_vectors.append(vec)
                        valid_metas.append(
                            {
                                "path": img.path,
                                "filename": img.filename,
                                "library_id": library_id,
                            }
                        )
                    else:
                        logger.warning(
                            f"Failed to generate embedding for {batch_images[idx].path}"
                        )

                if valid_ids:
                    store.add_batch(valid_ids, valid_vectors, valid_metas)
                    count += len(valid_ids)

                logger.info(f"Processed {count}/{total_images} embeddings")

                if progress_callback:
                    progress_callback(
                        count, total_images, f"Processed {count}/{total_images} images"
                    )

                # Reset batch
                batch_images = []
                batch_image_bytes = []

        except Exception as e:
            logger.error(f"Failed to prepare embedding batch for {image.path}: {e}")

    # Process remaining
    if batch_images:
        try:
            vectors = get_image_embeddings_batch(batch_image_bytes, model_name)

            valid_ids = []
            valid_vectors = []
            valid_metas = []

            for idx, vec in enumerate(vectors):
                if vec is not None:
                    img = batch_images[idx]
                    valid_ids.append(img.id)
                    valid_vectors.append(vec)
                    valid_metas.append(
                        {
                            "path": img.path,
                            "filename": img.filename,
                            "library_id": library_id,
                        }
                    )

            if valid_ids:
                store.add_batch(valid_ids, valid_vectors, valid_metas)
                count += len(valid_ids)

            if progress_callback:
                progress_callback(count, total_images, "Finalizing...")
        except Exception as e:
            logger.error(f"Failed to process final batch: {e}")

    return count
