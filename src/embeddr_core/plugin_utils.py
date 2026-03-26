"""
Shared utilities for Embeddr plugins.

Common helpers that reduce boilerplate across plugins. Import these
instead of reimplementing the same patterns:

    from embeddr_core.plugin_utils import brand_capabilities, normalize_artifact_id
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from embeddr_core.models.lotus import LotusCapability


def brand_capabilities(
    capabilities: List[LotusCapability],
    *,
    icon_url: Optional[str] = None,
    badge: Optional[str] = None,
) -> List[LotusCapability]:
    """
    Apply default UI branding (icon + badge) to a list of Lotus capabilities.

    This is a convenience function that sets ``iconUrl`` and ``badge`` in the
    capability's ``data.ui`` dict if not already set. Replaces the 6-line
    boilerplate loop that was copy-pasted across core plugins.

    Args:
        capabilities: The capabilities to brand.
        icon_url: Default icon URL (e.g. ``"/plugins/my-plugin/assets/logo.svg"``).
        badge: Default badge text (e.g. ``"My Plugin"``).

    Returns:
        The same list, mutated in-place for convenience.

    Example::

        def register_lotus(self):
            caps = [lotus.Action(...), lotus.Config(...)]
            return brand_capabilities(caps, icon_url=LOGO_URL, badge="My Plugin")
    """
    for cap in capabilities:
        data = cap.data or {}
        if isinstance(data, dict):
            ui = data.setdefault("ui", {})
            if isinstance(ui, dict):
                if icon_url is not None:
                    ui.setdefault("iconUrl", icon_url)
                if badge is not None:
                    ui.setdefault("badge", badge)
            cap.data = data
    return capabilities


def normalize_artifact_id(value: Any) -> Optional[UUID]:
    """
    Normalize an artifact ID from various input forms to UUID.

    Handles:
    - UUID instances (returned as-is)
    - Strings (parsed)
    - Dicts with an ``"id"`` key (extracted and parsed)
    - None / invalid values (returns None)

    Args:
        value: An artifact ID in any of the above forms.

    Returns:
        UUID or None if the value cannot be parsed.

    Example::

        artifact_id = normalize_artifact_id(inputs.get("artifact_id"))
        if not artifact_id:
            return {"ok": False, "error": "Invalid artifact ID"}
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, dict):
        value = value.get("id")
        if value is None:
            return None
    try:
        return UUID(str(value).strip())
    except (ValueError, AttributeError):
        return None


def normalize_artifact_ids(values: Any) -> List[UUID]:
    """
    Normalize a list of artifact IDs, filtering out invalid ones.

    Accepts a list of UUIDs, strings, or dicts with ``"id"`` keys.
    """
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    result = []
    for v in values:
        uid = normalize_artifact_id(v)
        if uid is not None:
            result.append(uid)
    return result
