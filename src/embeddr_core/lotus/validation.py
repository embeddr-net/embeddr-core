from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from embeddr_core.models.lotus import LotusCapability, LotusKind


@dataclass(frozen=True)
class CapabilityRequirement:
    raw: str
    kind: Optional[LotusKind] = None
    slot: Optional[str] = None
    capability_id: Optional[str] = None
    artifact_type: Optional[str] = None


def parse_requirement(req: str) -> CapabilityRequirement:
    raw = (req or "").strip()
    if raw.startswith("capability:"):
        return CapabilityRequirement(raw=req, capability_id=raw.split(":", 1)[1])
    if raw.startswith("artifact_type:"):
        return CapabilityRequirement(raw=req, artifact_type=raw.split(":", 1)[1])
    if raw.startswith("slot:"):
        return CapabilityRequirement(raw=req, slot=raw.split(":", 1)[1])

    if ":" in raw:
        head, tail = raw.split(":", 1)
        try:
            kind = LotusKind(head)
            return CapabilityRequirement(raw=req, kind=kind, slot=tail)
        except Exception:
            return CapabilityRequirement(raw=req, slot=raw)

    return CapabilityRequirement(raw=req, slot=raw)


def resolve_requirement(
    registry,
    requirement: CapabilityRequirement,
) -> bool:
    if requirement.capability_id:
        return registry.get(requirement.capability_id) is not None

    if requirement.artifact_type:
        for cap in registry.list(kind=LotusKind.artifact_type):
            data = cap.data or {}
            raw = data.get("types") or data.get("artifact_types") or []
            if isinstance(raw, dict):
                raw = [raw]
            if not isinstance(raw, list):
                continue
            for item in raw:
                if isinstance(item, dict) and item.get("name") == requirement.artifact_type:
                    return True
        return False

    if requirement.kind:
        return any(
            cap.kind == requirement.kind
            and requirement.slot
            and (cap.slot == requirement.slot or cap.id == requirement.slot)
            for cap in registry.list()
        )

    if requirement.slot:
        return any(
            cap.slot == requirement.slot or cap.id == requirement.slot
            for cap in registry.list()
        )

    return False
