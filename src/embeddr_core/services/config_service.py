from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel
from sqlmodel import Session, select, col
from sqlalchemy import or_

from embeddr_core.models.lotus import LotusKind
from embeddr_core.models.plugin_config import PluginConfig

logger = logging.getLogger("embeddr.core.config")


def _should_trace() -> bool:
    return os.environ.get("EMBEDDR_LOTUS_TRACE") == "1"


def _lazy_get_lotus_registry():
    try:
        from embeddr.core.plugin_loader import get_lotus_registry as _get_lotus_registry
    except Exception:
        return None
    return _get_lotus_registry


def get_lotus_registry():
    """
    Lazy accessor to avoid circular imports during plugin loading.
    """
    getter = _lazy_get_lotus_registry()
    if not getter:
        raise RuntimeError("Lotus registry unavailable")
    return getter()


def _redact(value: Dict[str, Any]) -> Dict[str, Any]:
    redacted = {}
    for k, v in (value or {}).items():
        if str(k).lower() in {"api_key", "apikey", "apiKey", "token", "authorization"}:
            redacted[k] = "***"
        else:
            redacted[k] = v
    return redacted


def _find_config_capability(plugin_name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Find the config capability for a plugin.
    Returns (cap_id, cap.data) or None.
    """
    getter = _lazy_get_lotus_registry()
    if not getter:
        return None

    reg = getter()
    caps = reg.list(kind=LotusKind.config, plugin=plugin_name)
    if not caps:
        return None
    # If you later have multiple scopes, pick the one with data.scope == global by default.
    cap = caps[0]
    return cap.id, (cap.data or {})


def _find_config_capability_by_id(cap_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    getter = _lazy_get_lotus_registry()
    if not getter:
        return None

    reg = getter()
    cap = reg.get(cap_id)
    if not cap or cap.kind != LotusKind.config:
        return None
    return cap.id, (cap.data or {})


def _schema_defaults(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract JSON schema defaults (best-effort).
    """
    out: Dict[str, Any] = {}
    props = (schema or {}).get("properties") or {}
    if isinstance(props, dict):
        for k, v in props.items():
            if isinstance(v, dict) and "default" in v:
                out[k] = v["default"]
    return out


def resolve_plugin_config(
    *,
    session: Session,
    plugin_name: str,
    scope: str = "global",
    scope_id: Optional[str] = None,
    config_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns the effective config:
      schema-defaults < capability.input.defaults < stored-config
    """
    resolved_config_id = config_id
    if config_id and plugin_name and not config_id.startswith(f"{plugin_name}."):
        resolved_config_id = f"{plugin_name}.{config_id}"

    cap_info = _find_config_capability_by_id(
        resolved_config_id) if resolved_config_id else _find_config_capability(plugin_name)
    if not cap_info:
        if _should_trace():
            logger.info(
                "[ConfigTrace] no config capability plugin=%s config_id=%s",
                plugin_name,
                config_id,
            )
        return {}

    _, data = cap_info
    input_block = data.get("input") or {}
    schema = input_block.get("schema") or {}
    cap_defaults = input_block.get("defaults") or {}

    effective: Dict[str, Any] = {}
    effective.update(_schema_defaults(schema))
    if isinstance(cap_defaults, dict):
        effective.update(cap_defaults)

    effective_plugin = plugin_name
    if resolved_config_id:
        getter = _lazy_get_lotus_registry()
        if getter:
            reg = getter()
            cap = reg.get(resolved_config_id)
            if cap and cap.plugin:
                effective_plugin = cap.plugin

    config_key = resolved_config_id or "default"

    stmt = select(PluginConfig).where(
        PluginConfig.plugin_name == effective_plugin,
        or_(
            col(PluginConfig.config_id) == config_key,
            col(PluginConfig.config_id).is_(None),
        ),
        PluginConfig.scope == scope,
        col(PluginConfig.scope_id).is_(
            None) if scope_id is None else PluginConfig.scope_id == scope_id,
    )
    row = session.exec(stmt).first()
    if row and isinstance(row.value, dict):
        effective.update(row.value)

    if _should_trace():
        logger.info(
            "[ConfigTrace] plugin=%s config_id=%s config_key=%s cap_id=%s defaults=%s row_found=%s value=%s",
            plugin_name,
            resolved_config_id,
            config_key,
            cap_info[0],
            _redact(cap_defaults if isinstance(cap_defaults, dict) else {}),
            bool(row),
            _redact(row.value if row and isinstance(row.value, dict) else {}),
        )

    return effective


def resolve_plugin_config_for_plugin(
    *,
    plugin_name: str,
    scope: str = "global",
    scope_id: Optional[str] = None,
    config_id: Optional[str] = None,
    engine: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Convenience helper that manages the DB session.
    """
    if engine is None:
        try:
            from embeddr.db.session import get_engine  # type: ignore
        except Exception as exc:  # pragma: no cover - optional runtime import
            raise RuntimeError(
                "No database engine available for config lookup") from exc
        engine = get_engine()

    with Session(engine) as session:
        return resolve_plugin_config(
            session=session,
            plugin_name=plugin_name,
            scope=scope,
            scope_id=scope_id,
            config_id=config_id,
        )


def set_plugin_config(
    *,
    session: Session,
    plugin_name: str,
    value: Dict[str, Any],
    scope: str = "global",
    scope_id: Optional[str] = None,
    config_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate (if model exists), then persist.
    """
    resolved_config_id = config_id
    if config_id and plugin_name and not config_id.startswith(f"{plugin_name}."):
        resolved_config_id = f"{plugin_name}.{config_id}"

    cap_info = _find_config_capability_by_id(
        resolved_config_id) if resolved_config_id else _find_config_capability(plugin_name)
    if not cap_info:
        raise ValueError(
            f"No config capability registered for plugin: {plugin_name}")

    _, data = cap_info
    input_block = data.get("input") or {}
    model_path = input_block.get("model")

    if isinstance(model_path, str) and model_path.strip():
        Model = _import_pydantic_model(model_path)
        obj = Model.model_validate(value or {})
        value = obj.model_dump()

    effective_plugin = plugin_name
    if resolved_config_id:
        getter = _lazy_get_lotus_registry()
        if getter:
            reg = getter()
            cap = reg.get(resolved_config_id)
            if cap and cap.plugin:
                effective_plugin = cap.plugin

    config_key = resolved_config_id or "default"

    stmt = select(PluginConfig).where(
        PluginConfig.plugin_name == effective_plugin,
        PluginConfig.config_id == config_key,
        PluginConfig.scope == scope,
        col(PluginConfig.scope_id).is_(
            None) if scope_id is None else PluginConfig.scope_id == scope_id,
    )
    row = session.exec(stmt).first()
    if not row:
        row = PluginConfig(
            plugin_name=effective_plugin,
            config_id=config_key,
            scope=scope,
            scope_id=scope_id,
            value=value,
        )
        session.add(row)
    else:
        row.value = value
        session.add(row)

    row.updated_at = datetime.now(timezone.utc)
    session.commit()

    return resolve_plugin_config(
        session=session,
        plugin_name=effective_plugin,
        scope=scope,
        scope_id=scope_id,
        config_id=config_key,
    )


def _import_pydantic_model(model_path: str) -> type[BaseModel]:
    """
    Import "pkg.module:ClassName" -> BaseModel subclass.
    Keep this local and simple; you already have a more robust importer in MCP.
    """
    import importlib

    if ":" not in model_path:
        raise ValueError(f"Invalid model path: {model_path}")
    mod_name, cls_name = model_path.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name, None)
    if cls is None:
        raise ValueError(f"Model class not found: {model_path}")
    if not issubclass(cls, BaseModel):
        raise ValueError(f"Model is not BaseModel: {model_path}")
    return cls
