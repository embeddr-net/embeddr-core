import json
import logging
import time
from typing import List, Optional, Dict, Any
from uuid import UUID

import numpy as np
from sqlmodel import Session, select

from embeddr_core.models.artifact_embedding import ArtifactEmbedding
from embeddr_core.services.config_service import resolve_plugin_config
from embeddr_core.services.vector_index import vector_index_registry, VectorIndexEntry

logger = logging.getLogger("embeddr.plugin.embeddr-vector-index.search")


class VectorStoreService:
    """
    Manages vector embeddings using the ArtifactEmbedding table for definition
    and in-memory numpy/faiss indexes for search.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        # Cache of loaded vectors: { model_name: { space: (ids, vectors) } }
        self._cache = {}

    def _resolve_backend_name(self, session: Optional[Session] = None) -> str:
        from contextlib import nullcontext

        ctx = nullcontext(session) if session else self.session_factory()
        try:
            with ctx as active_session:
                cfg = resolve_plugin_config(
                    session=active_session,
                    plugin_name="embeddr-vector-index",
                    scope="global",
                    scope_id=None,
                    config_id="embeddr-vector-index.config",
                )
            backend = cfg.get("backend") if isinstance(cfg, dict) else None
            if isinstance(backend, str) and backend:
                return backend
        except Exception:
            logger.exception("Failed to resolve vector index backend config")
        return "db"

    def _resolve_log_search(self, session: Optional[Session] = None) -> bool:
        from contextlib import nullcontext

        ctx = nullcontext(session) if session else self.session_factory()
        try:
            with ctx as active_session:
                cfg = resolve_plugin_config(
                    session=active_session,
                    plugin_name="embeddr-vector-index",
                    scope="global",
                    scope_id=None,
                    config_id="embeddr-vector-index.config",
                )
            if isinstance(cfg, dict):
                return bool(cfg.get("log_search"))
        except Exception:
            logger.exception("Failed to resolve vector index log_search config")
        return False

    def _resolve_backend(self, session: Optional[Session] = None):
        backend_name = self._resolve_backend_name(session)
        backend = vector_index_registry.get(backend_name)
        if not backend and backend_name != "db":
            logger.warning(
                "Vector index backend '%s' not registered; falling back to db",
                backend_name,
            )
        return backend, backend_name

    def get_connector(self, model_name: str, space: str = "default"):
        """
        Returns a helper object for a specific model/space.
        """
        return VectorSpaceConnector(self, model_name, space)

    def add_embedding(self, session: Session, artifact_id: UUID, vector: List[float],
                      model_name: str, vector_dim: int, space: str = "default",
                      plugin_name: str = "unknown"):
        """
        Persists an embedding to the database.
        """
        # Check if exists
        existing = session.exec(
            select(ArtifactEmbedding).where(
                ArtifactEmbedding.artifact_id == artifact_id,
                ArtifactEmbedding.model_name == model_name,
                ArtifactEmbedding.space == space
            )
        ).first()

        if existing:
            # Update (optional, maybe we want to guard against overwrite?)
            existing.vector_json = vector
            existing.plugin_name = plugin_name
            existing.created_at = existing.created_at  # Keep original creation or update?
            session.add(existing)
        else:
            emb = ArtifactEmbedding(
                artifact_id=artifact_id,
                model_name=model_name,
                vector_dim=vector_dim,
                vector_json=vector,
                space=space,
                plugin_name=plugin_name
            )
            session.add(emb)

        # Invalidate cache for this space
        self._invalidate_cache(model_name, space)

        backend, backend_name = self._resolve_backend(session)
        if backend and backend_name != "db":
            try:
                backend.upsert(
                    session,
                    [
                        VectorIndexEntry(
                            artifact_id=artifact_id,
                            model_name=model_name,
                            space=space,
                            vector=vector,
                            vector_dim=vector_dim,
                            plugin_name=plugin_name,
                        )
                    ],
                )
            except Exception:
                logger.exception(
                    "Vector index upsert failed backend=%s",
                    backend_name,
                )

    def search(self, query_vector: List[float], model_name: str,
               limit: int = 50, space: str = "default", session: Optional[Session] = None) -> List[Dict[str, Any]]:
        """
        Performs a similarity search using in-memory index.
        Loads index from DB if not cached.
        """
        start = time.perf_counter()
        log_search = self._resolve_log_search(session)
        backend, backend_name = self._resolve_backend(session)
        if backend and backend_name != "db":
            from contextlib import nullcontext

            ctx = nullcontext(session) if session else self.session_factory()
            with ctx as active_session:
                results = backend.search(
                    active_session,
                    query_vector=query_vector,
                    model_name=model_name,
                    space=space,
                    limit=limit,
                )
            out = [
                {"artifact_id": item.artifact_id, "score": item.score}
                for item in results
            ]
            if log_search:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                logger.info(
                    "vector.search backend=%s model=%s space=%s limit=%s took_ms=%.2f",
                    backend_name,
                    model_name,
                    space,
                    limit,
                    elapsed_ms,
                )
            return out

        ids, vectors = self._load_index(model_name, space, session=session)
        if not ids:
            return []

        query_np = np.array([query_vector]).astype('float32')
        # Normalize query if using cosine similarity (assumes vectors are normalized)

        # Simple dot product search (numpy) - good for small datasets (<100k)
        # For larger, would use FAISS here.
        scores = np.dot(vectors, query_np.T).flatten()

        # Get top-k
        # argsort sorts ascending, so take last k and reverse
        top_k_indices = np.argsort(scores)[-limit:][::-1]

        results = []
        for idx in top_k_indices:
            results.append({
                "artifact_id": ids[idx],
                "score": float(scores[idx])
            })

        if log_search:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.info(
                "vector.search backend=%s model=%s space=%s limit=%s took_ms=%.2f",
                backend_name,
                model_name,
                space,
                limit,
                elapsed_ms,
            )
        return results

    def _load_index(self, model_name: str, space: str, session: Optional[Session] = None):
        key = f"{model_name}:{space}"
        if key in self._cache:
            return self._cache[key]

        logger.info(
            f"Loading vector index for {model_name}/{space} from DB...")

        from contextlib import nullcontext
        ctx = nullcontext(session) if session else self.session_factory()

        with ctx as session:
            # Fetch all embeddings for this model/space
            # Warning: accurate but memory heavy for millions of rows.
            # Production would use PGVector or dedicated vector DB.
            statement = select(ArtifactEmbedding.artifact_id, ArtifactEmbedding.vector_json)\
                .where(ArtifactEmbedding.model_name == model_name)\
                .where(ArtifactEmbedding.space == space)

            results = session.exec(statement).all()

            if not results:
                self._cache[key] = ([], np.array([]))
                return [], np.array([])

            ids = [r[0] for r in results]
            # Convert list of floats to numpy array
            vectors = np.array([r[1] for r in results]).astype('float32')

            self._cache[key] = (ids, vectors)
            logger.info(f"Loaded {len(ids)} vectors.")
            return ids, vectors

    def _invalidate_cache(self, model_name: str, space: str):
        key = f"{model_name}:{space}"
        if key in self._cache:
            del self._cache[key]


class VectorSpaceConnector:
    """Helper for a specific model/space context"""

    def __init__(self, service: VectorStoreService, model_name: str, space: str):
        self.service = service
        self.model_name = model_name
        self.space = space

    def add(self, session: Session, artifact_id: UUID, vector: List[float], dim: int):
        self.service.add_embedding(
            session, artifact_id, vector, self.model_name, dim, self.space)

    def search(self, query_vector: List[float], limit: int = 50):
        return self.service.search(query_vector, self.model_name, limit, self.space)

        self.dirty = True
        self.save()

    def delete(self, ids_to_delete: list[int]):
        if not ids_to_delete:
            return

        ids_set = set(ids_to_delete)

        # Identify indices to keep
        indices_to_keep = [i for i, id in enumerate(
            self.ids) if id not in ids_set]

        if len(indices_to_keep) == len(self.ids):
            return  # Nothing to delete

        # Filter data
        self.ids = [self.ids[i] for i in indices_to_keep]
        self.metadata = [self.metadata[i] for i in indices_to_keep]

        if self.embeddings is not None:
            self.embeddings = self.embeddings[indices_to_keep]

        # Rebuild index
        self.id_to_index = {id: i for i, id in enumerate(self.ids)}

        self.dirty = True
        self.save()

    def get_vector_by_id(self, id: int) -> np.ndarray:
        if id in self.id_to_index:
            return self.embeddings[self.id_to_index[id]]
        return None

    def update_metadata(self, id: int, meta_update: dict):
        if id in self.id_to_index:
            idx = self.id_to_index[id]
            self.metadata[idx].update(meta_update)
            self.dirty = True

    def save(self):
        if not self.dirty:
            return

        # Simple approach: Re-shard everything (inefficient for huge data, but fine for <100k)
        # This ensures consistency and handles the "sharding" requirement.

        total_vectors = len(self.ids)
        if total_vectors == 0:
            return

        num_shards = (total_vectors + SHARD_SIZE - 1) // SHARD_SIZE

        for i in range(num_shards):
            start_idx = i * SHARD_SIZE
            end_idx = min((i + 1) * SHARD_SIZE, total_vectors)

            shard_data = self.embeddings[start_idx:end_idx]
            shard_meta = self.metadata[start_idx:end_idx]

            shard_filename = self.storage_path / f"shard_{i:05d}.npy"
            meta_filename = self.storage_path / f"meta_{i:05d}.json"

            np.save(shard_filename, shard_data)
            with open(meta_filename, "w") as f:
                json.dump(shard_meta, f)

        self.dirty = False

    def search(
        self,
        query_vector: np.ndarray,
        limit: int = 20,
        offset: int = 0,
        filter: dict = None,
        allowed_ids: set = None,
    ) -> list[tuple[int, float]]:
        if self.embeddings is None or len(self.embeddings) == 0:
            return []

        # Cosine similarity
        scores = np.dot(self.embeddings, query_vector)

        # Sort all scores descending
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        count = 0
        skipped = 0

        for idx in sorted_indices:
            # Check allowed_ids first (fastest)
            if allowed_ids is not None and self.ids[idx] not in allowed_ids:
                continue

            # Apply filter if provided
            if filter:
                meta = self.metadata[idx]
                match = True
                for k, v in filter.items():
                    # Handle type mismatch (e.g. int vs str) loosely if needed, but strict is safer
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            if skipped < offset:
                skipped += 1
                continue

            results.append((self.ids[idx], float(scores[idx])))
            count += 1

            if count >= limit:
                break

        return results


_stores = {}


def get_vector_store(model_name: str = "openai/clip-vit-base-patch32"):
    # Sanitize model name for filesystem
    safe_name = model_name.replace("/", "_").replace(":", "_")

    if safe_name not in _stores:
        _stores[safe_name] = VectorStore(model_name=safe_name)
    return _stores[safe_name]
