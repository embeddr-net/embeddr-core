"""
Shared async↔sync bridge utility.

Provides a safe way to call async coroutines from synchronous code,
regardless of whether an event loop is already running.

Usage:
    from embeddr_core.async_compat import run_sync
    result = run_sync(some_async_function())
"""
from __future__ import annotations

import asyncio
import logging
from threading import Thread
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_sync(coro: Any) -> Any:
    """
    Run an async coroutine from synchronous code.

    Strategy:
    - If there IS a running event loop (e.g. inside FastAPI/uvicorn),
      spawn a daemon thread with its own loop to avoid nested asyncio.run().
    - If there is NO running loop, call asyncio.run() directly.

    This is the canonical pattern used across Embeddr plugins and services.
    Extracted from the comfyui lotus_handlers thread-bridge.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an event loop — can't call asyncio.run() here.
        # Spawn a short-lived thread with its own loop.
        result: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def _runner() -> None:
            try:
                result["value"] = asyncio.run(coro)
            except BaseException as exc:
                error["error"] = exc

        t = Thread(target=_runner, daemon=True)
        t.start()
        t.join()

        if "error" in error:
            raise error["error"]
        return result.get("value")

    return asyncio.run(coro)
