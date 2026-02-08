"""Typed Lotus capability helpers."""

from typing import Any, Dict, Optional

from embeddr_core.models.lotus import LotusAction, LotusCapability, LotusKind, LotusQuery, LotusUI


class UI(LotusUI):
    """UI metadata helper for Lotus capabilities."""


class Action(LotusCapability):
    """Lotus action capability helper."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        action: Optional[str] = None,
        job_type: Optional[str] = None,
        exec: Optional[Dict[str, Any]] = None,
        expose: Optional[Dict[str, Any]] = None,
        input: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        action_payload = LotusAction(
            action=action,
            job_type=job_type,
            exec=exec or {},
            expose=expose or {},
            input=input,
            output=output,
        )
        super().__init__(
            id=id,
            kind=LotusKind.action,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            action=action_payload,
            data=data or {},
            **kwargs,
        )


class Feature(LotusCapability):
    """Lotus feature capability helper (action-like)."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        action: Optional[str] = None,
        job_type: Optional[str] = None,
        exec: Optional[Dict[str, Any]] = None,
        expose: Optional[Dict[str, Any]] = None,
        input: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        action_payload = LotusAction(
            action=action,
            job_type=job_type,
            exec=exec or {},
            expose=expose or {},
            input=input,
            output=output,
        )
        super().__init__(
            id=id,
            kind=LotusKind.feature,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            action=action_payload,
            data=data or {},
            **kwargs,
        )


class Resolver(LotusCapability):
    """Lotus resolver capability helper (read/query-style)."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        query: Optional[str] = None,
        slot: Optional[str] = None,
        input: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        query_payload = LotusQuery(
            query=query,
            slot=slot,
            input=input,
            output=output,
        )
        super().__init__(
            id=id,
            kind=LotusKind.resolver,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            query=query_payload,
            data=data or {},
            **kwargs,
        )


class ResolverAction(LotusCapability):
    """Lotus resolver capability helper (action-like resolvers)."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        action: Optional[str] = None,
        job_type: Optional[str] = None,
        exec: Optional[Dict[str, Any]] = None,
        expose: Optional[Dict[str, Any]] = None,
        input: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        slot: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        action_payload = LotusAction(
            action=action,
            job_type=job_type,
            exec=exec or {},
            expose=expose or {},
            input=input,
            output=output,
        )
        super().__init__(
            id=id,
            kind=LotusKind.resolver,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            action=action_payload,
            slot=slot,
            data=data or {},
            **kwargs,
        )


class Query(Resolver):
    """Alias for Resolver for query semantics."""


class Config(LotusCapability):
    """Lotus config capability helper."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        scope: str = "global",
        input: Optional[Dict[str, Any]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        payload = {
            "type": "config",
            "plugin": plugin,
            "scope": scope,
        }
        if input is not None:
            payload["input"] = input
        if defaults is not None:
            payload["defaults"] = defaults
        if data:
            payload.update(data)

        super().__init__(
            id=id,
            kind=LotusKind.config,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            data=payload,
            **kwargs,
        )


class Provider(LotusCapability):
    """Lotus provider capability helper."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            id=id,
            kind=LotusKind.provider,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            data=data or {},
            **kwargs,
        )


class ArtifactType(LotusCapability):
    """Lotus artifact type capability helper."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        types: Optional[list[Dict[str, Any]]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        payload = dict(data or {})
        if types is not None:
            payload["types"] = types
        super().__init__(
            id=id,
            kind=LotusKind.artifact_type,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            data=payload,
            **kwargs,
        )


class Transport(LotusCapability):
    """Lotus transport capability helper."""

    def __init__(
        self,
        *,
        id: str,
        title: str,
        plugin: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        requires: Optional[list[str]] = None,
        provides: Optional[list[str]] = None,
        ui: Optional[LotusUI] = None,
        links: Optional[list[Dict[str, Any]]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        payload = dict(data or {})
        if links is not None:
            payload["links"] = links

        super().__init__(
            id=id,
            kind=LotusKind.transport,
            title=title,
            description=description,
            plugin=plugin,
            version=version,
            tags=tags or [],
            requires=requires or [],
            provides=provides or [],
            ui=ui,
            data=payload,
            **kwargs,
        )
