from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol
from uuid import UUID

import numpy as np
from sqlmodel import Session, select
from sqlalchemy import delete

from embeddr_core.models.artifact_embedding import ArtifactEmbedding
from embeddr_core.services.config_service import resolve_plugin_config

logger = logging.getLogger(__name__)


@dataclass
class VectorIndexEntry:
    artifact_id: UUID
    model_name: str
    space: str
    vector: List[float]
    vector_dim: int
    plugin_name: str = "unknown"


@dataclass
class VectorSearchResult:
    artifact_id: UUID
    score: float


class VectorIndexBackend(Protocol):
    name: str

    def upsert(self, session: Session, entries: Iterable[VectorIndexEntry]) -> int:
        ...

    def search(
        self,
        session: Session,
        *,
        query_vector: List[float],
        model_name: str,
        space: str = "default",
        limit: int = 50,
    ) -> List[VectorSearchResult]:
        ...

    def reindex(
        self,
        session: Session,
        *,
        model_name: Optional[str] = None,
        space: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class DbVectorIndexBackend:
    name = "db"

    def upsert(self, session: Session, entries: Iterable[VectorIndexEntry]) -> int:
        count = 0
        for entry in entries:
            existing = session.exec(
                select(ArtifactEmbedding)
                .where(ArtifactEmbedding.artifact_id == entry.artifact_id)
                .where(ArtifactEmbedding.model_name == entry.model_name)
                .where(ArtifactEmbedding.space == entry.space)
            ).first()
            if existing:
                existing.vector_json = entry.vector
                existing.vector_dim = entry.vector_dim
                existing.plugin_name = entry.plugin_name
                session.add(existing)
            else:
                session.add(
                    ArtifactEmbedding(
                        artifact_id=entry.artifact_id,
                        model_name=entry.model_name,
                        space=entry.space,
                        vector_dim=entry.vector_dim,
                        vector_json=entry.vector,
                        plugin_name=entry.plugin_name,
                    )
                )
            count += 1
        return count

    def search(
        self,
        session: Session,
        *,
        query_vector: List[float],
        model_name: str,
        space: str = "default",
        limit: int = 50,
    ) -> List[VectorSearchResult]:
        rows = session.exec(
            select(ArtifactEmbedding.artifact_id,
                   ArtifactEmbedding.vector_json)
            .where(ArtifactEmbedding.model_name == model_name)
            .where(ArtifactEmbedding.space == space)
        ).all()
        if not rows:
            return []

        ids = [row[0] for row in rows]
        vectors = np.array([row[1] for row in rows]).astype("float32")
        query_np = np.array([query_vector]).astype("float32")
        scores = np.dot(vectors, query_np.T).flatten()

        top_k = np.argsort(scores)[-limit:][::-1]
        return [
            VectorSearchResult(artifact_id=ids[idx], score=float(scores[idx]))
            for idx in top_k
        ]

    def reindex(
        self,
        session: Session,
        *,
        model_name: Optional[str] = None,
        space: Optional[str] = None,
    ) -> Dict[str, Any]:
        stmt = select(ArtifactEmbedding)
        if model_name:
            stmt = stmt.where(ArtifactEmbedding.model_name == model_name)
        if space:
            stmt = stmt.where(ArtifactEmbedding.space == space)
        count = len(session.exec(stmt).all())
        return {
            "ok": True,
            "backend": self.name,
            "reindexed": count,
            "model_name": model_name,
            "space": space,
        }


class VectorIndexRegistry:
    def __init__(self) -> None:
        self._backends: Dict[str, VectorIndexBackend] = {}

    def register(self, backend: VectorIndexBackend) -> None:
        self._backends[backend.name] = backend

    def get(self, name: str) -> Optional[VectorIndexBackend]:
        return self._backends.get(name)

    def list_backends(self) -> List[str]:
        return sorted(self._backends.keys())


vector_index_registry = VectorIndexRegistry()
vector_index_registry.register(DbVectorIndexBackend())


class PgVectorIndexBackend:
    name = "pgvector"

    def __init__(self) -> None:
        from embeddr_core.models.artifact_embedding_pg import ArtifactEmbeddingPg

        self._model = ArtifactEmbeddingPg

    def upsert(self, session: Session, entries: Iterable[VectorIndexEntry]) -> int:
        count = 0
        for entry in entries:
            existing = session.exec(
                select(self._model)
                .where(self._model.artifact_id == entry.artifact_id)
                .where(self._model.model_name == entry.model_name)
                .where(self._model.space == entry.space)
            ).first()
            if existing:
                existing.vector = entry.vector
                existing.vector_dim = entry.vector_dim
                existing.plugin_name = entry.plugin_name
                session.add(existing)
            else:
                session.add(
                    self._model(
                        artifact_id=entry.artifact_id,
                        model_name=entry.model_name,
                        space=entry.space,
                        vector_dim=entry.vector_dim,
                        vector=entry.vector,
                        plugin_name=entry.plugin_name,
                    )
                )
            count += 1
        return count

    def search(
        self,
        session: Session,
        *,
        query_vector: List[float],
        model_name: str,
        space: str = "default",
        limit: int = 50,
    ) -> List[VectorSearchResult]:
        distance = self._model.vector.cosine_distance(query_vector)
        stmt = (
            select(self._model.artifact_id, distance.label("distance"))
            .where(self._model.model_name == model_name)
            .where(self._model.space == space)
            .order_by(distance)
            .limit(limit)
        )
        rows = session.exec(stmt).all()
        return [
            VectorSearchResult(
                artifact_id=row[0],
                score=float(1.0 - float(row[1])),
            )
            for row in rows
        ]

    def reindex(
        self,
        session: Session,
        *,
        model_name: Optional[str] = None,
        space: Optional[str] = None,
    ) -> Dict[str, Any]:
        delete_stmt = delete(self._model)
        if model_name:
            delete_stmt = delete_stmt.where(self._model.model_name == model_name)
        if space:
            delete_stmt = delete_stmt.where(self._model.space == space)
        session.exec(delete_stmt)

        stmt = select(ArtifactEmbedding)
        if model_name:
            stmt = stmt.where(ArtifactEmbedding.model_name == model_name)
        if space:
            stmt = stmt.where(ArtifactEmbedding.space == space)

        rows = session.exec(stmt).all()
        entries = [
            VectorIndexEntry(
                artifact_id=row.artifact_id,
                model_name=row.model_name,
                space=row.space,
                vector=row.vector_json,
                vector_dim=row.vector_dim,
                plugin_name=row.plugin_name or "unknown",
            )
            for row in rows
        ]
        self.upsert(session, entries)
        return {
            "ok": True,
            "backend": self.name,
            "reindexed": len(entries),
            "model_name": model_name,
            "space": space,
        }


try:  # pragma: no cover - optional backend
    vector_index_registry.register(PgVectorIndexBackend())
except Exception:
    logger.info("pgvector backend not available; skipping registration")


class ChromaVectorIndexBackend:
    name = "chroma"

    def _resolve_config(self, session: Session) -> Dict[str, Any]:
        cfg = resolve_plugin_config(
            session=session,
            plugin_name="embeddr-vector-index",
            scope="global",
            scope_id=None,
            config_id="embeddr-vector-index.config",
        )
        return cfg if isinstance(cfg, dict) else {}

    def _client(self, session: Session):
        cfg = self._resolve_config(session)
        mode = cfg.get("chroma_mode") or "http"
        if mode == "local":
            path = cfg.get("chroma_path") or "./chroma"
            return self._chroma.PersistentClient(path=path)
        host = cfg.get("chroma_host") or "localhost"
        port = int(cfg.get("chroma_port") or 8000)
        return self._chroma.HttpClient(host=host, port=port)

    def _collection_name(self, session: Session, model_name: str, space: str) -> str:
        cfg = self._resolve_config(session)
        prefix = cfg.get("chroma_collection_prefix") or "embeddr_"
        raw = f"{prefix}{model_name}__{space}"
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw)
        return safe[:63]

    def _collection(self, session: Session, model_name: str, space: str):
        name = self._collection_name(session, model_name, space)
        client = self._client(session)
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, session: Session, entries: Iterable[VectorIndexEntry]) -> int:
        entries_list = list(entries)
        if not entries_list:
            return 0
        sample = entries_list[0]
        collection = self._collection(session, sample.model_name, sample.space)
        ids = [str(entry.artifact_id) for entry in entries_list]
        embeddings = [entry.vector for entry in entries_list]
        metadatas = [
            {
                "model_name": entry.model_name,
                "space": entry.space,
                "plugin_name": entry.plugin_name,
                "vector_dim": entry.vector_dim,
            }
            for entry in entries_list
        ]
        collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
        return len(entries_list)

    def search(
        self,
        session: Session,
        *,
        query_vector: List[float],
        model_name: str,
        space: str = "default",
        limit: int = 50,
    ) -> List[VectorSearchResult]:
        collection = self._collection(session, model_name, space)
        result = collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            include=["distances"],
        )
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        out: List[VectorSearchResult] = []
        for idx, artifact_id in enumerate(ids):
            distance = float(distances[idx]) if idx < len(distances) else 0.0
            score = 1.0 - distance
            out.append(
                VectorSearchResult(artifact_id=UUID(str(artifact_id)), score=score)
            )
        return out

    def reindex(
        self,
        session: Session,
        *,
        model_name: Optional[str] = None,
        space: Optional[str] = None,
    ) -> Dict[str, Any]:
        stmt_pairs = select(ArtifactEmbedding.model_name, ArtifactEmbedding.space)
        if model_name:
            stmt_pairs = stmt_pairs.where(ArtifactEmbedding.model_name == model_name)
        if space:
            stmt_pairs = stmt_pairs.where(ArtifactEmbedding.space == space)
        pairs = session.exec(stmt_pairs.distinct()).all()
        total = 0
        client = self._client(session)

        for pair in pairs:
            pair_model = pair[0]
            pair_space = pair[1]
            collection_name = self._collection_name(session, pair_model, pair_space)
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass
            collection = self._collection(session, pair_model, pair_space)

            stmt = select(ArtifactEmbedding).where(
                ArtifactEmbedding.model_name == pair_model,
                ArtifactEmbedding.space == pair_space,
            )
            rows = session.exec(stmt).all()
            if not rows:
                continue
            entries = [
                VectorIndexEntry(
                    artifact_id=row.artifact_id,
                    model_name=row.model_name,
                    space=row.space,
                    vector=row.vector_json,
                    vector_dim=row.vector_dim,
                    plugin_name=row.plugin_name or "unknown",
                )
                for row in rows
            ]
            ids = [str(entry.artifact_id) for entry in entries]
            embeddings = [entry.vector for entry in entries]
            metadatas = [
                {
                    "model_name": entry.model_name,
                    "space": entry.space,
                    "plugin_name": entry.plugin_name,
                    "vector_dim": entry.vector_dim,
                }
                for entry in entries
            ]
            collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
            total += len(entries)

        return {
            "ok": True,
            "backend": self.name,
            "reindexed": total,
            "model_name": model_name,
            "space": space,
        }


try:  # pragma: no cover - optional backend
    import chromadb as _chromadb

    ChromaVectorIndexBackend._chroma = _chromadb
    vector_index_registry.register(ChromaVectorIndexBackend())
except Exception:
    logger.info("chroma backend not available; skipping registration")
