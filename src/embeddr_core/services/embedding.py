import logging
import numpy as np

# This service is now just an interface.
# Implementations are injected by plugins (e.g., embeddr-embeddings).

logger = logging.getLogger(__name__)


def _not_implemented(*args, **kwargs):
    raise NotImplementedError(
        "No embedding provider registered. Ensure 'embeddr-embeddings' plugin is loaded.")


# Default stubs that raise error if patched
# Plugins should overwrite these
get_text_embedding = _not_implemented
get_image_embedding = _not_implemented
get_image_embeddings_batch = _not_implemented
def get_loaded_model_name(): return None
def unload_model(): return None


def load_model(model_name: str):
    pass
