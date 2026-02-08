"""Zen UI component helpers."""

from embeddr_core.plugin_interface import (
    PanelComponent,
    PanelUI,
    DockComponent,
    DockUI,
    PageComponent,
    WidgetComponent,
    ConfigRendererComponent,
)


class Panel(PanelComponent):
    """Zen panel registration."""


class PanelOptions(PanelUI):
    """Typed options for Zen panels."""


class Dock(DockComponent):
    """Zen dock registration."""


class DockOptions(DockUI):
    """Typed options for Zen docks."""


class Page(PageComponent):
    """Zen page registration."""


class Widget(WidgetComponent):
    """Zen widget registration."""


class ConfigRenderer(ConfigRendererComponent):
    """Zen config renderer registration."""


__all__ = [
    "Panel",
    "PanelOptions",
    "Dock",
    "DockOptions",
    "Page",
    "Widget",
    "ConfigRenderer",
]
