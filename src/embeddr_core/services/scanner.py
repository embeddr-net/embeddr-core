import logging
import mimetypes
import os
from pathlib import Path

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
    if not root_path.exists():
        logger.warning(f"Library path not found: {root_path}")
        return 0

    added_count = 0

    # Get existing images for this library to avoid duplicates
    # For large libraries, this might need optimization (e.g. set of paths)
    existing_paths = set(
        session.exec(
            select(LocalImage.path).where(LocalImage.library_path_id == library_path.id)
        ).all()
    )

    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                str_path = str(file_path)

                if str_path in existing_paths:
                    continue

                # Basic metadata
                try:
                    stat = file_path.stat()
                    file_size = stat.st_size
                except OSError:
                    file_size = 0

                mime_type, _ = mimetypes.guess_type(file_path)

                # Create image record
                image = LocalImage(
                    path=str_path,
                    filename=file,
                    library_path_id=library_path.id,
                    file_size=file_size,
                    mime_type=mime_type,
                )
                session.add(image)
                added_count += 1

                # Commit in batches if needed, but for now simple

    session.commit()
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
