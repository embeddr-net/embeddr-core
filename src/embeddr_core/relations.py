from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Literal, Tuple


@dataclass(frozen=True)
class RelationTypeDef:
    name: str
    family: str
    direction: Literal["forward", "reverse", "bidirectional"] = "forward"
    inverse: str | None = None
    transitive: bool = False
    structural: bool = False


RELATION_TYPE_DEFS: Dict[str, RelationTypeDef] = {
    "contains": RelationTypeDef(
        name="contains",
        family="containment",
        direction="forward",
        inverse="contained_in",
        transitive=True,
        structural=True,
    ),
    "group": RelationTypeDef(
        name="group",
        family="containment",
        direction="forward",
        inverse="member_of",
        transitive=True,
        structural=True,
    ),
    "contained_in": RelationTypeDef(
        name="contained_in",
        family="containment",
        direction="reverse",
        inverse="contains",
        transitive=False,
        structural=True,
    ),
    "member_of": RelationTypeDef(
        name="member_of",
        family="containment",
        direction="reverse",
        inverse="group",
        transitive=False,
        structural=True,
    ),
    "part_of": RelationTypeDef(
        name="part_of",
        family="semantic",
        direction="forward",
        transitive=False,
        structural=False,
    ),
    "reference": RelationTypeDef(
        name="reference",
        family="semantic",
        direction="forward",
        transitive=False,
        structural=False,
    ),
    "generates": RelationTypeDef(
        name="generates",
        family="workflow",
        direction="forward",
        inverse="generated_by",
        transitive=False,
        structural=False,
    ),
    "generated_by": RelationTypeDef(
        name="generated_by",
        family="workflow",
        direction="reverse",
        inverse="generates",
        transitive=False,
        structural=False,
    ),
}


STRUCTURAL_PARENT_TO_CHILD: Tuple[str, ...] = ("contains", "group")
STRUCTURAL_CHILD_TO_PARENT: Tuple[str, ...] = ("contained_in", "member_of")
STRUCTURAL_RELATION_TYPES: Tuple[str, ...] = (
    *STRUCTURAL_PARENT_TO_CHILD,
    *STRUCTURAL_CHILD_TO_PARENT,
)


def structural_relation_types(
    direction: Literal["down", "up", "both"] = "both",
) -> Tuple[str, ...]:
    if direction == "down":
        return STRUCTURAL_PARENT_TO_CHILD
    if direction == "up":
        return STRUCTURAL_CHILD_TO_PARENT
    return STRUCTURAL_RELATION_TYPES


def is_structural_relation_type(relation_type: str | None) -> bool:
    if not relation_type:
        return False
    return relation_type in STRUCTURAL_RELATION_TYPES


def normalize_relation_types(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in values if v))
