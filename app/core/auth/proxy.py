"""Trusted reverse-proxy boundary for client address handling."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

WSGIApp = Callable[..., Iterable[bytes]]
IPNetwork = IPv4Network | IPv6Network


class TrustedProxyMiddleware:
    """Honor one forwarded hop only when the direct peer is trusted."""

    def __init__(self, app: WSGIApp, trusted_networks: tuple[str, ...]) -> None:
        self._app: WSGIApp = app
        self._trusted_networks: tuple[IPNetwork, ...] = tuple(
            ip_network(network, strict=False) for network in trusted_networks if network
        )

    def __call__(self, environ, start_response) -> Iterable[bytes]:
        peer = environ.get("REMOTE_ADDR", "")
        try:
            peer_address = ip_address(peer)
        except ValueError:
            peer_address = None

        trusted = peer_address is not None and any(peer_address in network for network in self._trusted_networks)
        if not trusted:
            self._discard_forwarded_headers(environ)
            return self._app(environ, start_response)

        forwarded_for = environ.get("HTTP_X_FORWARDED_FOR", "")
        candidate = forwarded_for.rsplit(",", maxsplit=1)[-1].strip()
        try:
            _ = ip_address(candidate)
        except ValueError:
            _ = environ.pop("HTTP_X_FORWARDED_FOR", None)
        else:
            environ["REMOTE_ADDR"] = candidate
        _ = environ.pop("HTTP_X_FORWARDED_FOR", None)

        forwarded_proto = environ.get("HTTP_X_FORWARDED_PROTO", "")
        proto = forwarded_proto.rsplit(",", maxsplit=1)[-1].strip().lower()
        if proto in {"http", "https"}:
            environ["wsgi.url_scheme"] = proto
        _ = environ.pop("HTTP_X_FORWARDED_PROTO", None)

        for key in ("HTTP_X_FORWARDED_HOST", "HTTP_X_FORWARDED_PORT", "HTTP_X_FORWARDED_PREFIX"):
            _ = environ.pop(key, None)
        return self._app(environ, start_response)

    @staticmethod
    def _discard_forwarded_headers(environ) -> None:
        for key in tuple(environ):
            if key.startswith("HTTP_X_FORWARDED_"):
                _ = environ.pop(key, None)
