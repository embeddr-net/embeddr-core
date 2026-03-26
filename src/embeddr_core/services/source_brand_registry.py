"""Source brand registry — plugin-driven mapping of source namespaces to brand identity.

Plugins self-register their brand info during on_load() via PluginContext.register_source_brand().
The provenance system and taxonomy endpoint query this registry to resolve
human-readable names and icon URLs for source_namespace values.

Core provides ONLY the interface and in-memory store. No plugin-specific knowledge lives here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceBrand:
    """Brand identity for a source namespace."""
    namespace: str
    name: str
    icon_url: Optional[str] = None


class SourceBrandRegistry:
    """In-memory registry of source namespace → brand identity mappings.

    Plugins register their brands at startup. The registry is process-local
    and populated during plugin initialization.
    """

    def __init__(self) -> None:
        self._brands: Dict[str, SourceBrand] = {}

    def register(
        self,
        namespace: str,
        name: str,
        icon_url: Optional[str] = None,
    ) -> None:
        """Register a source brand. Plugins call this during on_load()."""
        namespace = namespace.strip()
        if not namespace:
            return
        brand = SourceBrand(namespace=namespace, name=name, icon_url=icon_url)
        if namespace in self._brands:
            logger.debug(
                "Overwriting source brand for '%s': %s -> %s",
                namespace, self._brands[namespace].name, name,
            )
        self._brands[namespace] = brand

    def resolve(self, namespace: str) -> Optional[SourceBrand]:
        """Resolve a namespace to its brand, or None if not registered."""
        return self._brands.get(namespace)

    def resolve_or_default(self, namespace: str) -> SourceBrand:
        """Resolve a namespace, falling back to a generic brand using the raw namespace as name."""
        brand = self._brands.get(namespace)
        if brand:
            return brand
        # Produce a readable fallback from the namespace
        fallback_name = namespace.replace("plugin:", "").replace("_", " ").replace("-", " ").title()
        return SourceBrand(namespace=namespace, name=fallback_name)

    def list_brands(self) -> Dict[str, SourceBrand]:
        """Return all registered brands."""
        return dict(self._brands)

    def to_dict(self) -> Dict[str, Dict[str, Optional[str]]]:
        """Serialize for API responses."""
        return {
            ns: {"name": brand.name, "icon_url": brand.icon_url}
            for ns, brand in self._brands.items()
        }


# Module-level singleton
_registry = SourceBrandRegistry()


def get_source_brand_registry() -> SourceBrandRegistry:
    return _registry
