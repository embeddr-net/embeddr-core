from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import httpx

logger = logging.getLogger("embeddr.services.http_client")

DEFAULT_TIMEOUT_S = 20.0
DEFAULT_HEADERS = {
    "User-Agent": "Embeddr/0.2 (+https://embeddr.net)",
}


@dataclass(frozen=True)
class FetchOptions:
    timeout_s: float = DEFAULT_TIMEOUT_S
    follow_redirects: bool = True
    headers: Optional[Mapping[str, str]] = None
    params: Optional[Mapping[str, Any]] = None
    proxies: Optional[Mapping[str, str]] = None


def _merge_headers(headers: Optional[Mapping[str, str]]) -> dict[str, str]:
    merged = dict(DEFAULT_HEADERS)
    if headers:
        merged.update(headers)
    return merged


def _normalize_proxy_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return raw
    if "://" in raw:
        return raw
    return f"http://{raw}"


def _pick_proxy(proxies: Optional[Mapping[str, str]]) -> Optional[str]:
    if not proxies:
        return None
    for key in ("https://", "http://"):
        if key in proxies and proxies[key]:
            return _normalize_proxy_url(str(proxies[key]))
    for value in proxies.values():
        if value:
            return _normalize_proxy_url(str(value))
    return None


def _looks_like_html(text: str) -> bool:
    probe = (text or "").strip().lower()
    if not probe:
        return False
    return "<html" in probe[:400] or "<body" in probe[:400]


def request(
    method: str,
    url: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    follow_redirects: bool = True,
    headers: Optional[Mapping[str, str]] = None,
    params: Optional[Mapping[str, Any]] = None,
    proxies: Optional[Mapping[str, str]] = None,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> httpx.Response:
    client_headers = _merge_headers(headers)
    client_kwargs: dict[str, Any] = {
        "timeout": timeout_s,
        "follow_redirects": follow_redirects,
        "headers": client_headers,
    }
    if proxies:
        normalized = {k: _normalize_proxy_url(
            str(v)) for k, v in proxies.items() if v}
        client_kwargs["proxies"] = normalized

    try:
        with httpx.Client(**client_kwargs) as client:
            response = client.request(method, url, params=params, **kwargs)
            if raise_for_status:
                response.raise_for_status()
            return response
    except TypeError:
        proxy_value = _pick_proxy(proxies)
        client_kwargs.pop("proxies", None)
        if proxy_value:
            try:
                with httpx.Client(**{**client_kwargs, "proxy": proxy_value}) as client:
                    response = client.request(
                        method, url, params=params, **kwargs)
                    if raise_for_status:
                        response.raise_for_status()
                    return response
            except TypeError:
                pass
        with httpx.Client(**client_kwargs) as client:
            response = client.request(method, url, params=params, **kwargs)
            if raise_for_status:
                response.raise_for_status()
            return response


def fetch_text(
    url: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    follow_redirects: bool = True,
    headers: Optional[Mapping[str, str]] = None,
    params: Optional[Mapping[str, Any]] = None,
    proxies: Optional[Mapping[str, str]] = None,
    reject_html: bool = False,
) -> str:
    response = request(
        "GET",
        url,
        timeout_s=timeout_s,
        follow_redirects=follow_redirects,
        headers=headers,
        params=params,
        proxies=proxies,
        raise_for_status=True,
    )
    text = response.text
    if reject_html and _looks_like_html(text):
        return ""
    return text


# ---------------------------------------------------------------------------
# Shared proxy resolution
# ---------------------------------------------------------------------------

def resolve_http_proxy(
    *,
    session: Any = None,
) -> Optional[Dict[str, str]]:
    """Resolve the default HTTP proxy from the embeddr-http plugin config.

    Reads the ``embeddr-http`` plugin's stored configuration (global scope)
    and returns a proxy mapping suitable for passing to ``httpx.Client``.
    Returns ``None`` when no proxy is configured or the plugin has no config.

    If *session* is ``None`` one is created internally (requires the
    ``embeddr.db.session`` runtime to be available).
    """
    try:
        from embeddr_core.services.config_service import resolve_plugin_config

        owns_session = session is None
        if owns_session:
            from embeddr.db.session import get_engine
            from sqlmodel import Session as _Session
            session = _Session(get_engine())

        try:
            cfg = resolve_plugin_config(
                session=session,
                plugin_name="embeddr-http",
                scope="global",
                scope_id=None,
                config_id="embeddr-http.config",
            )
            if not cfg:
                cfg = resolve_plugin_config(
                    session=session,
                    plugin_name="embeddr-http",
                    scope="global",
                    scope_id=None,
                    config_id=None,
                )
        finally:
            if owns_session:
                session.close()

        if not cfg:
            return None

        default_id = str(cfg.get("default_proxy_id") or "").strip()
        if not default_id:
            return None

        proxies_list = cfg.get("proxies") or []
        proxy_entry: Optional[Dict[str, Any]] = None
        for entry in proxies_list:
            if not isinstance(entry, dict):
                continue
            if entry.get("id") == default_id or (entry.get("name") and entry.get("name") == default_id):
                proxy_entry = entry
                break

        if not proxy_entry or not proxy_entry.get("url"):
            return None

        url = str(proxy_entry["url"]).strip()
        if "://" not in url:
            url = f"http://{url}"

        logger.debug("Resolved HTTP proxy: id=%s url=%s", proxy_entry.get("id"), url)
        return {"http://": url, "https://": url}

    except Exception as exc:
        logger.debug("Failed to resolve HTTP proxy config: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Streaming download
# ---------------------------------------------------------------------------

def _build_client_kwargs(
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    follow_redirects: bool = True,
    proxies: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    """Build kwargs dict for ``httpx.Client`` with proxy compat handling."""
    kw: dict[str, Any] = {
        "timeout": timeout_s,
        "follow_redirects": follow_redirects,
        "headers": _merge_headers(headers),
    }
    if proxies:
        normalized = {k: _normalize_proxy_url(str(v)) for k, v in proxies.items() if v}
        kw["proxies"] = normalized
    return kw


def _open_client(kwargs: dict[str, Any], proxies: Optional[Mapping[str, str]] = None) -> httpx.Client:
    """Create an httpx.Client, handling the proxies/proxy API break."""
    try:
        return httpx.Client(**kwargs)
    except TypeError:
        kwargs.pop("proxies", None)
        proxy_value = _pick_proxy(proxies)
        if proxy_value:
            try:
                return httpx.Client(**{**kwargs, "proxy": proxy_value})
            except TypeError:
                pass
        return httpx.Client(**kwargs)


def stream_download(
    url: str,
    destination: Path,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout_s: float = 120.0,
    proxies: Optional[Mapping[str, str]] = None,
    follow_redirects: bool = True,
) -> int:
    """Stream-download *url* to *destination* with optional proxy routing.

    Writes to a ``.part`` temp file first, then atomically renames.
    Returns the number of bytes written.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".part")
    bytes_written = 0
    client_kwargs = _build_client_kwargs(
        headers=headers,
        timeout_s=timeout_s,
        follow_redirects=follow_redirects,
        proxies=proxies,
    )
    with _open_client(client_kwargs, proxies) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with temp_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    handle.write(chunk)
                    bytes_written += len(chunk)
    temp_path.replace(destination)
    return bytes_written
