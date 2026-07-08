"""Exception types raised by the Qint SDK."""

from __future__ import annotations

from typing import Any, Dict, Optional


class QintError(Exception):
    """Base class for every error raised by this SDK."""


class QintConnectionError(QintError):
    """The request never produced an HTTP response (DNS, TCP, TLS, timeout)."""


class QintApiError(QintError):
    """A non-2xx HTTP response.

    Carries the HTTP ``status_code`` and, when the body is an RFC 7807
    ``application/problem+json`` document, the parsed ``detail`` / ``title`` /
    ``type`` fields. The full parsed body (or raw text) is kept on ``problem``.
    """

    def __init__(
        self,
        status_code: int,
        detail: Optional[str] = None,
        *,
        title: Optional[str] = None,
        type: Optional[str] = None,
        problem: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.title = title
        self.type = type
        self.problem = problem or {}
        self.body = body
        message = detail or title or body or f"HTTP {status_code}"
        super().__init__(f"[{status_code}] {message}")


class QintWebhookSignatureError(QintError):
    """The webhook signature header did not match the computed HMAC."""
