import logging
import mimetypes
import os
from pathlib import Path
from uuid import uuid4
from typing import Optional, List

from sqlmodel import Session, select

from embeddr_core.models.artifact import Artifact
from embeddr_core.models.artifact_relation import ArtifactRelation
from embeddr_core.models.tag import Tag, ArtifactTagLink
from embeddr_core.services.scanner_registry import scanner_registry, Scanner

logger = logging.getLogger(__name__)

# Basic extension mapping to artifact types
# In a real plugin system, plugins would register these extensions
EXTENSION_MAP = {
    # Images
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
    ".gif": "image", ".bmp": "image", ".tiff": "image",
    # Text
    ".txt": "text", ".md": "text", ".json": "text",
    # PDFs
    ".pdf": "document",
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
        root_path = Path(root)

        # 1. Handle Directory Artifact
        dir_uri = str(root_path)
        dir_art = session.exec(select(Artifact).where(
            Artifact.uri == dir_uri)).first()

        if not dir_art:
            dir_art = Artifact(
                id=uuid4(),
                type_name="folder",
                uri=dir_uri,
                metadata_json={
                    "filename": root_path.name,
                    "scanner": "embeddr-core:filesystem"
                }
            )
            session.add(dir_art)
            session.flush()  # Ensure ID is available
            added_count += 1

        for filename in files:
            file_path = Path(root) / filename
            ext = file_path.suffix.lower()

            # Determine type (fallback to 'file')
            art_type = EXTENSION_MAP.get(ext, "file")

            # TODO: Check excludes/ignore patterns here

            # Check if artifact already exists by URI
            # Using str(file_path) as the URI for local files
            uri = str(file_path)

            # Simple existence check
            existing = session.exec(
                select(Artifact).where(Artifact.uri == uri)
            ).first()

            target_artifact = existing
            if not existing:
                # Create the artifact
                target_artifact = Artifact(
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
                session.add(target_artifact)
                session.flush()  # Ensure ID
                added_count += 1

            # Ensure Relation: Directory (Contains) -> File
            # Check if relation exists
            rel_exists = session.get(
                ArtifactRelation, (dir_art.id, target_artifact.id))
            if not rel_exists:
                relation = ArtifactRelation(
                    source_id=dir_art.id,
                    target_id=target_artifact.id,
                    relation_type="contains",
                    source_namespace="embeddr-core:scanner"
                )
                session.add(relation)

            # Commit periodically
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


class LocalFileSystemScanner(Scanner):
    def scan(self, session: Session, artifact: Artifact, recursive: bool = True) -> int:
        if not artifact.uri:
            logger.warning(
                f"Artifact {artifact.id} has no URI, cannot scan filesystem.")
            return 0
        return scan_path(session, artifact.uri, recursive=recursive)


# Register the default scanner
scanner_registry.register("collection:directory", LocalFileSystemScanner())


class ManualCollectionScanner(Scanner):
    """
    A scanner for manual collections (e.g. 'collection:mix') that does not
    scan any external source, but allows the collection to exist in the registry.
    """

    def scan(self, session: Session, artifact: Artifact, recursive: bool = True) -> int:
        # Manual collections are populated by user action, not scanning
        return 0


scanner_registry.register("collection:mix", ManualCollectionScanner())
