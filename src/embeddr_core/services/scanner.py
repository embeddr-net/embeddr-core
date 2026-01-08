import logging
import mimetypes
import os
from pathlib import Path
from uuid import uuid4
from typing import Optional, List

from sqlmodel import Session, select

from embeddr_core.models.artifact import Artifact
from embeddr_core.models.tag import Tag, ArtifactTagLink

logger = logging.getLogger(__name__)

# Basic extension mapping to artifact types
# In a real plugin system, plugins would register these extensions
EXTENSION_MAP = {
    # Images
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
    ".gif": "image", ".bmp": "image", ".tiff": "image",
    # Text
    ".txt": "text", ".md": "text", ".json": "text",
    # Audio
    ".mp3": "audio", ".wav": "audio", ".flac": "audio"
}


def scan_path(session: Session, root_path: str, recursive: bool = True) -> int:
    """
    Scans a filesystem path and creates Artifacts for found files.
    Returns the number of new artifacts created.
    """
    path_obj = Path(root_path).resolve()
    logger.info(f"Starting scan of: {path_obj}")

    if not path_obj.exists():
        logger.warning(f"Path not found: {path_obj}")
        return 0

    added_count = 0
    total_scanned = 0

    # Walk the directory
    for root, dirs, files in os.walk(path_obj):
        for filename in files:
            file_path = Path(root) / filename
            ext = file_path.suffix.lower()

            # Determine type (fallback to 'file')
            art_type = EXTENSION_MAP.get(ext, "file")

            # TODO: Check excludes/ignore patterns here

            # Check if artifact already exists by URI
            # Using str(file_path) as the URI for local files
            uri = str(file_path)

            # Simple existence check (could be optimized with a pre-fetched set for large dirs)
            existing = session.exec(
                select(Artifact).where(Artifact.uri == uri)
            ).first()

            if not existing:
                # Create the artifact
                artifact = Artifact(
                    id=uuid4(),
                    type_name=art_type,
                    uri=uri,
                    metadata_json={
                        "filename": filename,
                        "extension": ext,
                        "size": file_path.stat().st_size,
                        "scanner": "embeddr-core:filesystem"
                    }
                )
                session.add(artifact)
                added_count += 1

                # Commit every 100 items to avoid massive transactions
                if added_count % 100 == 0:
                    session.commit()

            total_scanned += 1
            if total_scanned % 500 == 0:
                logger.info(
                    f"Scanned {total_scanned} files, added {added_count} artifacts...")

        if not recursive:
            break

    session.commit()
    logger.info(
        f"Scan complete. Scanned {total_scanned}, Added {added_count}.")
    return added_count
