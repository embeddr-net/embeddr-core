from typing import Protocol, Type, Dict, Optional, Any
from uuid import UUID
from sqlmodel import Session
from embeddr_core.models.artifact import Artifact


class Scanner(Protocol):
    """
    Interface for a scanner that can populate a library root artifact
    with child artifacts.
    """

    def scan(self, session: Session, artifact: Artifact, recursive: bool = True) -> int:
        """
        Scan the given artifact (which represents a collection/root) 
        and populate children.
        """
        ...

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return a JSON schema or dictionary describing available configuration options.
        For UI generation.
        """
        return {}


class ScannerRegistry:
    def __init__(self):
        self._scanners: Dict[str, Scanner] = {}

    def register(self, artifact_type: str, scanner: Scanner):
        """Register a scanner for a specific artifact type (e.g. 'collection:directory')."""
        self._scanners[artifact_type] = scanner

    def get_scanner(self, artifact_type: str) -> Optional[Scanner]:
        return self._scanners.get(artifact_type)


class ManualCollectionScanner:
    """Default scanner for manual collections that does nothing."""

    def scan(self, session: Session, artifact: Artifact, recursive: bool = True) -> int:
        return 0

    def get_config_schema(self) -> Dict[str, Any]:
        return {}


# Global registry instance
scanner_registry = ScannerRegistry()
scanner_registry.register("collection:mix", ManualCollectionScanner())
