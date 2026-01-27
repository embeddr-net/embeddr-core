"""Zen UI component helpers."""

from embeddr_core.plugin_interface import (
    PanelComponent,
    PageComponent,
    WidgetComponent,
)


class Panel(PanelComponent):
    """Zen panel registration."""


class Page(PageComponent):
    """Zen page registration."""


class Widget(WidgetComponent):
    """Zen widget registration."""


__all__ = ["Panel", "Page", "Widget"]
