"""HTTP transport abstraction.

The default transport uses only the standard library (:mod:`urllib`). Tests (or
advanced users) can inject any object implementing :class:`Transport` to avoid
real network I/O — this is what keeps the SDK fully mockable and offline-testable.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, Mapping, Optional

try:  # pragma: no cover - typing-only convenience
    from typing import Protocol
except ImportError:  # pragma: no cover - Python < 3.8 fallback
    Protocol = object  # type: ignore[assignment,misc]

from .errors import QintConnectionError


@dataclass
class HttpResponse:
    """A minimal, transport-agnostic HTTP response."""

    status: int
    body: bytes
    headers: Dict[str, str]

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Transport(Protocol):
    """Anything able to perform a single HTTP request.

    Implementations MUST return an :class:`HttpResponse` for any completed
    exchange, including 4xx/5xx responses (the client inspects the status), and
    raise :class:`~qint.errors.QintConnectionError` when no response arrives.
    """

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Optional[bytes] = None,
        timeout: float = 30.0,
    ) -> HttpResponse: ...


class UrllibTransport:
    """Default :class:`Transport` backed by :func:`urllib.request.urlopen`."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Optional[bytes] = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        req = urllib.request.Request(
            url, data=body, headers=dict(headers), method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return HttpResponse(
                    status=resp.status,
                    body=resp.read(),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                )
        except urllib.error.HTTPError as exc:
            # A 4xx/5xx is still a real response — surface it to the client so it
            # can parse the problem+json body, rather than treating it as failure.
            return HttpResponse(
                status=exc.code,
                body=exc.read(),
                headers={k.lower(): v for k, v in (exc.headers or {}).items()},
            )
        except urllib.error.URLError as exc:
            raise QintConnectionError(f"Request to {url} failed: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:  # pragma: no cover - env dependent
            raise QintConnectionError(f"Request to {url} failed: {exc}") from exc
