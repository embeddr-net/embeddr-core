import json
import os
from pathlib import Path

import numpy as np


def get_vector_store_path():
    return Path(os.environ.get("EMBEDDR_VECTOR_STORAGE_DIR", "vector_storage"))


SHARD_SIZE = 1000  # Number of embeddings per shard


class VectorStore:
    def __init__(self, storage_path: Path = None, model_name: str = "default"):
        if storage_path is None:
            storage_path = get_vector_store_path()
        self.storage_path = storage_path / model_name
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.embeddings = None
        self.ids = []
        self.metadata = []
        self.id_to_index = {}
        self.dirty = False
        self.load_shards()

    def load_shards(self):
        # Load all shards into memory for now (simple search)
        self.embeddings = None
        self.ids = []
        self.metadata = []

        shard_files = sorted(list(self.storage_path.glob("shard_*.npy")))
        for shard_file in shard_files:
            shard_id = shard_file.stem.split("_")[1]
            meta_file = self.storage_path / f"meta_{shard_id}.json"

            if meta_file.exists():
                shard_emb = np.load(shard_file)
                with open(meta_file) as f:
                    shard_meta = json.load(f)

                if self.embeddings is None:
                    self.embeddings = shard_emb
                else:
                    self.embeddings = np.concatenate(
                        (self.embeddings, shard_emb), axis=0
                    )

                self.ids.extend([m["id"] for m in shard_meta])
                self.metadata.extend(shard_meta)

        # Create ID lookup map
        self.id_to_index = {id: i for i, id in enumerate(self.ids)}

        count = len(self.ids)
        print(f"Loaded {count} embeddings from {len(shard_files)} shards.")

    def add(
        self, id: int, vector: np.ndarray, meta: dict = None, auto_save: bool = True
    ):
        # Add to memory
        if self.embeddings is None:
            self.embeddings = np.array([vector])
        else:
            self.embeddings = np.vstack([self.embeddings, vector])

        self.ids.append(id)
        self.metadata.append({"id": id, **(meta or {})})
        self.id_to_index[id] = len(self.ids) - 1
        self.dirty = True

        if auto_save:
            self.save()

    def add_batch(
        self, ids: list[int], vectors: list[np.ndarray], metas: list[dict] = None
    ):
        if not ids:
            return

        if metas is None:
            metas = [{}] * len(ids)

        # Convert vectors to numpy array if list
        vectors_arr = np.array(vectors)

        if self.embeddings is None:
            self.embeddings = vectors_arr
        else:
            self.embeddings = np.vstack([self.embeddings, vectors_arr])

        start_idx = len(self.ids)
        self.ids.extend(ids)

        for i, (id, meta) in enumerate(zip(ids, metas)):
            self.metadata.append({"id": id, **(meta or {})})
            self.id_to_index[id] = start_idx + i

        self.dirty = True
        self.save()

    def delete(self, ids_to_delete: list[int]):
        if not ids_to_delete:
            return

        ids_set = set(ids_to_delete)

        # Identify indices to keep
        indices_to_keep = [i for i, id in enumerate(self.ids) if id not in ids_set]

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
