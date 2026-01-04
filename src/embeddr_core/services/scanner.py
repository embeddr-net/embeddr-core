import logging
import mimetypes
import os
from pathlib import Path

import imagehash
from PIL import Image
from sqlmodel import Session, select

from embeddr_core.models.library import LibraryPath, LocalImage

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


def scan_library_path(session: Session, library_path: LibraryPath) -> int:
    """
    Scans a library path for images and adds them to the database.
    Returns the number of new images added.
    """
    root_path = Path(library_path.path)
    lib_name = library_path.name or library_path.path
    logger.info(f"Starting scan of library: {lib_name} ({root_path})")

    if not root_path.exists():
        logger.warning(f"Library path not found: {root_path}")
        return 0

    added_count = 0

    # Get existing images for this library to avoid duplicates
    # For large libraries, this might need optimization (e.g. set of paths)
    existing_paths = set(
        session.exec(
            select(LocalImage.path).where(
                LocalImage.library_path_id == library_path.id)
        ).all()
    )
    logger.info(
        f"Found {len(existing_paths)} existing images in database for {lib_name}")

    total_scanned = 0
    for root, dirs, files in os.walk(root_path):
        for file in files:
            total_scanned += 1
            if total_scanned % 100 == 0:
                logger.info(
                    f"Scanning {lib_name}: Checked {total_scanned} files, found {added_count} new images so far..."
                )

            file_path = Path(root) / file
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                str_path = str(file_path)

                if str_path in existing_paths:
                    logger.debug(f"Skipping existing image: {file}")
                    continue

                # Basic metadata
                try:
                    stat = file_path.stat()
                    file_size = stat.st_size
                except OSError:
                    file_size = 0

                mime_type, _ = mimetypes.guess_type(file_path)

                width = None
                height = None
                phash = None

                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        phash = str(imagehash.phash(img))
                except Exception as e:
                    logger.warning(
                        f"Failed to process image metadata for {file_path}: {e}")

                # Create image record
                image = LocalImage(
                    path=str_path,
                    filename=file,
                    library_path_id=library_path.id,
                    file_size=file_size,
                    mime_type=mime_type,
                    width=width,
                    height=height,
                    phash=phash,
                )
                session.add(image)
                added_count += 1
                logger.debug(f"Added new image: {file}")

                # Commit in batches if needed, but for now simple

    session.commit()
    logger.info(
        f"Finished scanning {lib_name}. Total files checked: {total_scanned}. New images added: {added_count}."
    )
    return added_count


def scan_all_libraries(session: Session) -> dict:
    """
    Scans all configured library paths.
    Returns a dict mapping library ID to count of added images.
    """
    libraries = session.exec(select(LibraryPath)).all()
    results = {}

    for lib in libraries:
        count = scan_library_path(session, lib)
        results[lib.id] = count

    return results
