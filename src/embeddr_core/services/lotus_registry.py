from __future__ import annotations

from typing import Dict, List, Optional

import logging

from embeddr_core.models.lotus import LotusCapability, LotusKind, LotusResult
from embeddr_core.models.schema_defs import normalize_schema
from embeddr_core.lotus.validation import parse_requirement, resolve_requirement

logger = logging.getLogger(__name__)


class LotusRegistry:
    def __init__(self) -> None:
        self._by_id: Dict[str, LotusCapability] = {}
        self._missing_requirements: Dict[str, List[str]] = {}

    def list_capabilities(self) -> list[LotusCapability]:
        return list(self._by_id.values())

    def register(self, cap: LotusCapability) -> None:
        if cap.data:
            data = cap.data.copy()
            for key in ("input", "output"):
                block = data.get(key)
                if isinstance(block, dict) and isinstance(block.get("schema"), dict):
                    block = block.copy()
                    block["schema"] = normalize_schema(block["schema"])
                    data[key] = block
            cap = cap.model_copy(update={"data": data})
        self._by_id[cap.id] = cap
        self._validate_capability(cap)
        self._check_dependencies(cap)

    def get(self, cap_id: str) -> Optional[LotusCapability]:
        return self._by_id.get(cap_id)

    def list(
        self,
        *,
        kind: LotusKind | None = None,
        slot: str | None = None,
        plugin: str | None = None,
    ) -> List[LotusCapability]:
        items = list(self._by_id.values())
        if kind is not None:
            items = [c for c in items if c.kind == kind]
        if slot is not None:
            items = [c for c in items if c.slot == slot]
        if plugin is not None:
            items = [c for c in items if c.plugin == plugin]
        return items

    def query(self, q: str, limit: int = 20) -> List[LotusResult]:
        qn = (q or "").strip().lower()

        def hay(c: LotusCapability) -> str:
            return f"{c.title} {c.description or ''} {c.id} {' '.join(c.tags)}".lower()

        caps = self.list()
        if qn:
            caps = [c for c in caps if qn in hay(c)]

        # trivial scoring for now: exact prefix/contains boosts later
        results = [LotusResult(capability=c, score=1.0) for c in caps]
        return results[: max(1, min(limit, 50))]

    def _validate_capability(self, cap: LotusCapability) -> None:
        data = cap.data or {}
        if cap.kind in {LotusKind.action, LotusKind.provider, LotusKind.resolver, LotusKind.indexer}:
            if not cap.slot:
                logger.warning("Lotus capability %s missing slot", cap.id)
        if cap.kind == LotusKind.action and not data.get("action"):
            logger.warning("Lotus action %s missing data.action", cap.id)
        if cap.kind == LotusKind.config and not data.get("input"):
            logger.warning("Lotus config %s missing data.input", cap.id)
        if cap.kind == LotusKind.nav and not data.get("route"):
            logger.warning("Lotus nav %s missing data.route", cap.id)

    def _check_dependencies(self, cap: LotusCapability) -> None:
        requires = list(cap.requires or [])
        data_requires = cap.data.get(
            "requires") if isinstance(cap.data, dict) else None
        if isinstance(data_requires, list):
            requires.extend(data_requires)

        missing: List[str] = []
        for req in requires:
            requirement = parse_requirement(req)
            if not resolve_requirement(self, requirement):
                missing.append(req)

        if missing:
            self._missing_requirements[cap.id] = missing
            logger.warning(
                "Lotus capability %s missing requirements: %s",
                cap.id,
                ", ".join(missing),
            )
        elif cap.id in self._missing_requirements:
            self._missing_requirements.pop(cap.id, None)

    def get_missing_requirements(self) -> Dict[str, List[str]]:
        return dict(self._missing_requirements)

    def recheck_dependencies(self) -> None:
        for cap in list(self._by_id.values()):
            self._check_dependencies(cap)
