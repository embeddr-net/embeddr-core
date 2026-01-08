from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class EmbeddrPlugin(ABC):
    """
    Base interface for all Embeddr plugins.
    Plugins must implement this to be loaded by the core.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the plugin, e.g. 'embeddr-comfyui'"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semver string"""
        pass

    @property
    def plugin_type(self) -> str:
        """One of: 'adapter', 'workflow', 'importer', 'exporter'"""
        return "adapter"

    @abstractmethod
    def register_types(self) -> List[Dict[str, Any]]:
        """
        Return a list of ArtifactType definitions to register.
        Format:
        [
            {
                "name": "image:comfy",
                "base_type": "image",
                "capabilities": {"edit": True}
            }
        ]
        """
        pass

    def register_capabilities(self) -> List[str]:
        """
        Return a list of capability keys this plugin introduces.
        """
        return []

    def on_load(self) -> None:
        """Called when plugin is loaded"""
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        pass
