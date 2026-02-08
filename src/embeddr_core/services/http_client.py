from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

import httpx

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
