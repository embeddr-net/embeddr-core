import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type, get_args, get_origin

from pydantic import BaseModel

from embeddr_core.plugin_interface import LotusPlugin, PluginContext

logger = logging.getLogger("embeddr.core.plugin_actions")

_INJECT_PARAM_NAMES = {"context", "ctx", "execution_id"}
_INPUTS_PARAM_NAMES = {"inputs", "payload", "data"}


@dataclass(frozen=True)
class ActionHandler:
    name: str
    func: Callable[..., Any]
    input_model: Optional[Type[BaseModel]]


@dataclass(frozen=True)
class ActionMeta:
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    requires: Optional[list[str]] = None
    exec: Optional[Dict[str, Any]] = None
    expose: Optional[Dict[str, Any]] = None
    ui: Optional[Any] = None
    input_ui: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ActionDefaults:
    tags: Optional[list[str]] = None
    requires: Optional[list[str]] = None
    exec: Optional[Dict[str, Any]] = None
    expose: Optional[Dict[str, Any]] = None
    ui: Optional[Any] = None
    input_ui: Optional[Dict[str, Any]] = None


# Default expose when none is specified – visible to all subsystems.
_DEFAULT_EXPOSE: Dict[str, Any] = {
    "lotus": True,
    "api": True,
    "mcp": True,
}


def action(
    name: str,
    *,
    input_model: Optional[Type[BaseModel]] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    requires: Optional[list[str]] = None,
    exec: Optional[Dict[str, Any]] = None,
    expose: Optional[Dict[str, Any]] = None,
    ui: Optional[Any] = None,
    input_ui: Optional[Dict[str, Any]] = None,
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "_embeddr_action_name", name)
        setattr(func, "_embeddr_action_input_model", input_model)
        setattr(
            func,
            "_embeddr_action_meta",
            ActionMeta(
                title=title,
                description=description,
                tags=tags,
                requires=requires,
                exec=exec,
                expose=expose,
                ui=ui,
                input_ui=input_ui,
            ),
        )
        return func

    return decorator


def build_lotus_actions(
    plugin: "ActionPlugin",
    *,
    defaults: Optional[ActionDefaults] = None,
    plugin_name: Optional[str] = None,
    version: Optional[str] = None,
    action_prefix: Optional[str] = None,
) -> list[Any]:
    from embeddr_core import lotus

    merged_defaults = defaults or ActionDefaults()
    name = plugin_name or plugin.name
    ver = version or plugin.version
    prefix = f"{action_prefix}." if action_prefix else ""

    actions: list[Any] = []
    for action_name, method in plugin._iter_action_methods():
        meta: ActionMeta = getattr(
            method, "_embeddr_action_meta", ActionMeta())
        input_model = getattr(
            method, "_embeddr_action_input_model", None) or _infer_input_model(method)
        input_payload = None
        if input_model:
            input_payload = {
                "model": f"{input_model.__module__}:{input_model.__qualname__}",
                "schema": input_model.model_json_schema(),
            }
            input_ui = meta.input_ui or merged_defaults.input_ui
            if input_ui:
                input_payload["ui"] = input_ui

        action_id = f"{prefix}{action_name}"
        title = meta.title or _title_from_action(action_name)
        description = meta.description
        tags = meta.tags if meta.tags is not None else merged_defaults.tags or []
        requires = (
            meta.requires
            if meta.requires is not None
            else merged_defaults.requires or []
        )
        exec_cfg = meta.exec if meta.exec is not None else merged_defaults.exec or {}
        expose = (
            meta.expose
            if meta.expose is not None
            else merged_defaults.expose or _DEFAULT_EXPOSE
        )
        ui = meta.ui if meta.ui is not None else merged_defaults.ui

        actions.append(
            lotus.Action(
                id=action_id,
                title=title,
                description=description,
                plugin=name,
                version=ver,
                tags=tags,
                requires=requires,
                ui=ui,
                action=action_name,
                exec=exec_cfg,
                expose=expose,
                input=input_payload,
            )
        )

    return actions


def _model_from_annotation(annotation: Any) -> Optional[Type[BaseModel]]:
    if annotation is inspect._empty:
        return None
    if annotation is PluginContext:
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation

    origin = get_origin(annotation)
    if origin is None:
        return None

    if origin is list or origin is dict:
        return None

    args = get_args(annotation)
    for arg in args:
        if arg is PluginContext:
            continue
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


def _title_from_action(action_name: str) -> str:
    return action_name.replace(".", " ").replace("_", " ").title()


def _infer_input_model(func: Callable[..., Any]) -> Optional[Type[BaseModel]]:
    sig = inspect.signature(func)
    model_type: Optional[Type[BaseModel]] = None
    for param in sig.parameters.values():
        if param.name == "self":
            continue
        if param.name in _INJECT_PARAM_NAMES:
            continue
        ann_model = _model_from_annotation(param.annotation)
        if not ann_model:
            continue
        if model_type and model_type is not ann_model:
            raise ValueError(
                "Action handler has multiple BaseModel inputs; "
                "specify input_model in @action."
            )
        model_type = ann_model
    return model_type


def _select_model_param(
    sig: inspect.Signature, model_type: Optional[Type[BaseModel]]
) -> Optional[str]:
    if model_type is None:
        return None

    selected: Optional[str] = None
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        ann_model = _model_from_annotation(param.annotation)
        if ann_model is model_type:
            if selected and selected != name:
                raise ValueError(
                    "Action handler has multiple parameters for the input model; "
                    "use a single BaseModel parameter."
                )
            selected = name

    if selected:
        return selected

    for name in sig.parameters:
        if name in _INJECT_PARAM_NAMES or name in _INPUTS_PARAM_NAMES:
            continue
        if name == "self":
            continue
        return name

    return None


def _normalize_output(result: Any) -> Dict[str, Any]:
    if isinstance(result, BaseModel):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    if result is None:
        return {"ok": True}
    return {"ok": True, "result": result}


class ActionPlugin(LotusPlugin):
    def execute(
        self,
        action_name: str,
        execution_id: Any,
        inputs: Dict[str, Any],
        context: Optional[PluginContext] = None,
    ) -> Dict[str, Any]:
        handler = self._get_action_handler(action_name)
        if handler is None:
            raise NotImplementedError(
                f"Plugin {self.name} does not support execution of {action_name}"
            )

        try:
            return self._invoke_action(handler, inputs, context, execution_id)
        except Exception as exc:
            logger.exception(
                "Action failed plugin=%s action=%s", self.name, action_name
            )
            return self.on_action_error(
                action_name=action_name,
                error=exc,
                inputs=inputs,
                context=context,
                execution_id=execution_id,
            )

    def on_action_error(
        self,
        action_name: str,
        error: Exception,
        inputs: Optional[Dict[str, Any]] = None,
        context: Optional[PluginContext] = None,
        execution_id: Any = None,
    ) -> Dict[str, Any]:
        return {"ok": False, "error": str(error)}

    def _get_action_handler(self, action_name: str) -> Optional[ActionHandler]:
        registry = getattr(self, "_action_registry_cache", None)
        if registry is None:
            registry = self._build_action_registry()
            setattr(self, "_action_registry_cache", registry)
        return registry.get(action_name)

    def _build_action_registry(self) -> Dict[str, ActionHandler]:
        registry: Dict[str, ActionHandler] = {}
        for action_name, method in self._iter_action_methods():
            explicit_model = getattr(
                method, "_embeddr_action_input_model", None)
            inferred_model = explicit_model or _infer_input_model(method)
            if action_name in registry:
                raise ValueError(
                    f"Duplicate action handler '{action_name}' on {self.name}"
                )
            registry[action_name] = ActionHandler(
                name=action_name,
                func=method,
                input_model=inferred_model,
            )
        return registry

    def _iter_action_methods(self):
        for _, member in inspect.getmembers(self, predicate=callable):
            action_name = getattr(member, "_embeddr_action_name", None)
            if action_name:
                yield action_name, member

    def _invoke_action(
        self,
        handler: ActionHandler,
        inputs: Optional[Dict[str, Any]],
        context: Optional[PluginContext],
        execution_id: Any,
    ) -> Dict[str, Any]:
        sig = inspect.signature(handler.func)
        model_value = (
            handler.input_model.model_validate(inputs or {})
            if handler.input_model
            else None
        )
        model_param = _select_model_param(sig, handler.input_model)
        kwargs: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if name in {"context", "ctx"}:
                kwargs[name] = context
                continue
            if name == "execution_id":
                kwargs[name] = execution_id
                continue
            if model_param and name == model_param:
                kwargs[name] = model_value
                continue
            if name in _INPUTS_PARAM_NAMES:
                kwargs[name] = inputs or {}
                continue

            ann_model = _model_from_annotation(param.annotation)
            if ann_model and model_value is not None:
                kwargs[name] = model_value
                continue

            if param.default is inspect._empty:
                raise ValueError(
                    f"Unhandled parameter '{name}' for action '{handler.name}'"
                )

        return _normalize_output(handler.func(**kwargs))
