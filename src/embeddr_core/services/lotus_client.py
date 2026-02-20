from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel
from sqlmodel import Session

from embeddr_core.models.lotus import LotusKind
from embeddr_core.services.config_service import resolve_plugin_config

logger = logging.getLogger("embeddr.core.lotus_client")


def _resolve_registry():
    try:
        from embeddr.core.plugin_loader import get_lotus_registry

        return get_lotus_registry()
    except Exception:
        return None


def _resolve_plugin(plugin_name: str):
    try:
        from embeddr.core.plugin_loader import get_all_plugin_instances

        for plugin in get_all_plugin_instances():
            if plugin.name == plugin_name:
                return plugin
    except Exception:
        return None
    return None


def _import_model(model_path: str) -> Optional[Type[BaseModel]]:
    if not model_path or ":" not in model_path:
        return None
    module_name, class_name = model_path.split(":", 1)
    try:
        module = __import__(module_name, fromlist=[class_name])
        model = getattr(module, class_name, None)
        if isinstance(model, type) and issubclass(model, BaseModel):
            return model
    except Exception:
        return None
    return None


def prepare_inputs(
    *,
    plugin_name: str,
    inputs: Dict[str, Any] | None,
    session: Session,
) -> Dict[str, Any]:
    raw_inputs = dict(inputs or {})
    clean_inputs = {k: v for k, v in raw_inputs.items() if v is not None}

    if len(clean_inputs) != len(raw_inputs):
        dropped = sorted(set(raw_inputs.keys()) - set(clean_inputs.keys()))
        logger.debug("Dropping None inputs for %s: %s", plugin_name, dropped)

    merged = dict(clean_inputs)

    config_id = None
    try:
        reg = _resolve_registry()
        if reg:
            caps = reg.list(kind=LotusKind.config, plugin=str(plugin_name))
            if caps:
                config_id = caps[0].id
    except Exception:
        config_id = None

    try:
        cfg = resolve_plugin_config(
            session=session,
            plugin_name=str(plugin_name),
            scope="global",
            scope_id=None,
            config_id=config_id,
        )
        if (not cfg) and config_id:
            cfg = resolve_plugin_config(
                session=session,
                plugin_name=str(plugin_name),
                scope="global",
                scope_id=None,
                config_id=None,
            )
        if isinstance(cfg, dict) and cfg:
            merged = {**cfg, **merged}
    except Exception as exc:
        logger.debug("Config load failed for %s: %s", plugin_name, exc)

    return merged


def invoke_action(
    *,
    cap_id: str,
    inputs: Dict[str, Any],
    session: Session,
    context: Any = None,
) -> Dict[str, Any]:
    registry = _resolve_registry()
    if not registry:
        raise ValueError("Lotus registry unavailable")

    cap = registry.get(cap_id)
    if not cap:
        raise ValueError(f"Capability not found: {cap_id}")
    if cap.kind != LotusKind.action:
        raise ValueError(f"Capability is not action: {cap_id}")

    data = cap.data or {}
    plugin_name = str(data.get("plugin") or cap.plugin or "")
    action_name = str(data.get("action") or "")
    if not plugin_name or not action_name:
        raise ValueError(f"Capability missing plugin/action: {cap_id}")

    merged_inputs = prepare_inputs(
        plugin_name=plugin_name,
        inputs=inputs or {},
        session=session,
    )

    if "__embeddr_auth" not in merged_inputs:
        payload: Dict[str, Any] = {}
        if isinstance(getattr(context, "inputs", None), dict):
            inherited = context.inputs.get("__embeddr_auth")
            if isinstance(inherited, dict):
                payload.update(inherited)

        for key in ("mode", "user_id", "operator_id", "api_key_id", "session_id"):
            value = getattr(context, key, None)
            if value is not None and key not in payload:
                payload[key] = str(value) if key.endswith("_id") else value

        for key in ("is_admin", "is_root", "is_open"):
            value = getattr(context, key, None)
            if value is not None and key not in payload:
                payload[key] = bool(value)

        permissions = getattr(context, "permissions", None)
        if permissions is not None and "permissions" not in payload:
            if isinstance(permissions, (set, tuple, list)):
                payload["permissions"] = [str(p) for p in permissions if p]
            elif permissions:
                payload["permissions"] = [str(permissions)]

        if payload:
            merged_inputs["__embeddr_auth"] = payload

    model_path = ((data.get("input") or {}).get("model") or "")
    Model = _import_model(str(model_path))
    if Model is not None:
        obj = Model.model_validate(merged_inputs)
        merged_inputs = obj.model_dump()

    plugin = _resolve_plugin(plugin_name)
    if not plugin:
        raise ValueError(f"Plugin not found: {plugin_name}")

    return plugin.execute(action_name, None, merged_inputs, context=context)


def invoke_action_for_plugin(
    *,
    cap_id: str,
    inputs: Dict[str, Any],
    context: Any = None,
    session: Optional[Session] = None,
    engine: Any = None,
) -> Dict[str, Any]:
    """
    Convenience helper that manages the DB session.
    """
    if session is not None:
        return invoke_action(cap_id=cap_id, inputs=inputs, session=session, context=context)

    if engine is None:
        try:
            from embeddr.db.session import get_engine  # type: ignore
        except Exception as exc:  # pragma: no cover - optional runtime import
            raise RuntimeError(
                "No database engine available for lotus invoke") from exc
        engine = get_engine()

    with Session(engine) as new_session:
        return invoke_action(
            cap_id=cap_id,
            inputs=inputs,
            session=new_session,
            context=context,
        )
