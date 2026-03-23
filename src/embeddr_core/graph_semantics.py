"""
Graph relation semantics — resolution utilities.

Previously this module contained a large hardcoded dict of plugin-specific
relation types (stash, agent, publishing, etc.). Those types are now registered
by plugins via PluginContext.register_relation_type() and stored in the
RelationTypeDef table.

This module handles:
  - Resolution of core built-in relation types (from relations.py)
  - Fallback resolution for unregistered types ("other" family)
  - Taxonomy building (DB-aware, called at request time)
  - Namespace grouping helpers
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from embeddr_core.relations import RELATION_TYPE_DEFS


@dataclass(frozen=True)
class RelationSemantics:
    canonical_type: str
    family: str
    description: str = ""


def _semantics_from_core(relation_type: str) -> Optional[RelationSemantics]:
    """Resolve against the built-in RELATION_TYPE_DEFS (core types only)."""
    rel_def = RELATION_TYPE_DEFS.get(relation_type)
    if rel_def:
        return RelationSemantics(
            canonical_type=relation_type,
            family=rel_def.family,
            description=f"Core relation ({rel_def.family}).",
        )
    return None


def get_relation_semantics(relation_type: str | None) -> RelationSemantics:
    """
    Resolve semantics for a relation type string.

    Resolution order:
      1. Core built-in types (RELATION_TYPE_DEFS)
      2. Unknown → family "other"

    For DB-registered plugin types, use get_relation_semantics_from_db()
    which accepts a session and checks the RelationTypeDef table.
    """
    relation = str(relation_type or "").strip()
    if not relation:
        return RelationSemantics(canonical_type="unknown", family="other", description="Missing relation type.")

    core = _semantics_from_core(relation)
    if core:
        return core

    return RelationSemantics(canonical_type=relation, family="other", description="Unregistered relation type.")


def get_relation_semantics_from_db(relation_type: str | None, session) -> RelationSemantics:
    """
    Resolve semantics for a relation type, checking the DB registry for
    plugin-registered types before falling back to "other".

    Use this in request handlers that have a DB session available.
    The hot-path BFS in graph_query_service uses get_relation_semantics()
    with a pre-loaded cache to avoid per-edge DB hits.
    """
    relation = str(relation_type or "").strip()
    if not relation:
        return RelationSemantics(canonical_type="unknown", family="other", description="Missing relation type.")

    core = _semantics_from_core(relation)
    if core:
        return core

    try:
        from embeddr_core.models.relation_type import RelationTypeDef
        from sqlmodel import select

        row = session.exec(select(RelationTypeDef).where(RelationTypeDef.name == relation)).first()
        if row:
            return RelationSemantics(
                canonical_type=row.name,
                family=row.family,
                description=row.description,
            )
    except Exception:
        pass

    return RelationSemantics(canonical_type=relation, family="other", description="Unregistered relation type.")


def canonical_relation_type(relation_type: str | None) -> str:
    return get_relation_semantics(relation_type).canonical_type


def relation_family(relation_type: str | None) -> str:
    return get_relation_semantics(relation_type).family


def relation_semantics_tuple(relation_type: str | None) -> Tuple[str, str]:
    sem = get_relation_semantics(relation_type)
    return sem.canonical_type, sem.family


def relation_taxonomy(
    additional_relation_types: Iterable[str] | None = None,
    session=None,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Build the full relation taxonomy for the /graph/taxonomy endpoint.

    When a session is provided, also includes plugin-registered types
    from the RelationTypeDef table. Pass additional_relation_types to
    include any raw strings observed in ArtifactRelation rows.
    """
    # Start from core built-ins
    relation_types: dict[str, RelationSemantics] = {
        name: RelationSemantics(
            canonical_type=name,
            family=rd.family,
            description=f"Core relation ({rd.family}).",
        )
        for name, rd in RELATION_TYPE_DEFS.items()
    }

    # Merge DB-registered plugin types
    if session is not None:
        try:
            from embeddr_core.models.relation_type import RelationTypeDef
            from sqlmodel import select

            rows = session.exec(select(RelationTypeDef)).all()
            for row in rows:
                if row.name not in relation_types:
                    relation_types[row.name] = RelationSemantics(
                        canonical_type=row.name,
                        family=row.family,
                        description=row.description,
                    )
        except Exception:
            pass

    # Merge any observed raw types (unregistered — family "other")
    if additional_relation_types:
        for rt in additional_relation_types:
            rt = str(rt).strip()
            if rt and rt not in relation_types:
                relation_types[rt] = RelationSemantics(
                    canonical_type=rt,
                    family="other",
                    description="Unregistered relation type.",
                )

    type_rows: List[Dict[str, str]] = []
    family_rows: Dict[str, Dict[str, str]] = {}

    for rel_name in sorted(relation_types):
        sem = relation_types[rel_name]
        type_rows.append(
            {
                "relation_type_raw": rel_name,
                "relation_type_canonical": sem.canonical_type,
                "relation_family": sem.family,
                "description": sem.description,
            }
        )
        family_rows.setdefault(
            sem.family,
            {
                "id": sem.family,
                "label": sem.family.replace("_", " ").title(),
            },
        )

    return {
        "families": sorted(family_rows.values(), key=lambda row: row["id"]),
        "types": type_rows,
    }


def normalize_namespace_group(namespace: str | None) -> str:
    value = str(namespace or "").strip()
    if not value:
        return "unknown"
    if value == "user":
        return "user"
    if value.startswith("plugin:"):
        return "plugin"
    if value.startswith("agent:"):
        return "agent"
    if value.startswith("system:"):
        return "system"
    return "other"
