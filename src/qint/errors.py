"""Exception types raised by the Qint SDK."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

#: The amount is outside the per-payment limits (HTTP 400 on create).
AMOUNT_OUT_OF_RANGE = "amount_out_of_range"
#: No exchange rate was available to judge the limits (HTTP 503 on create).
RATE_UNAVAILABLE = "rate_unavailable"

_STANDARD_PROBLEM_MEMBERS = frozenset({"type", "title", "status", "detail", "instance"})


def _decimal_or_none(value: Any) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001 - malformed extension: treat as absent
        return None


class QintError(Exception):
    """Base class for every error raised by this SDK."""


class QintConnectionError(QintError):
    """The request never produced an HTTP response (DNS, TCP, TLS, timeout)."""


class QintApiError(QintError):
    """A non-2xx HTTP response.

    Carries the HTTP ``status_code`` and, when the body is an RFC 7807
    ``application/problem+json`` document, the parsed ``detail`` / ``title`` /
    ``type`` fields. The full parsed body (or raw text) is kept on ``problem``.

    ``code`` is the problem's machine-readable error code, if any — for example
    ``"amount_out_of_range"`` (400) or ``"rate_unavailable"`` (503). The API
    serialises problem extensions flat at the top level; ``extensions`` holds
    every member beyond the standard RFC 7807 ones, and ``min_chf`` /
    ``max_chf`` / ``amount_chf`` expose the limit numbers as ``Decimal``.
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
        code = self.problem.get("code")
        self.code: Optional[str] = code if isinstance(code, str) else None
        message = detail or title or body or f"HTTP {status_code}"
        super().__init__(f"[{status_code}] {message}")

    @property
    def extensions(self) -> Dict[str, Any]:
        """Problem members beyond ``type``/``title``/``status``/``detail``/``instance``."""
        return {k: v for k, v in self.problem.items() if k not in _STANDARD_PROBLEM_MEMBERS}

    @property
    def min_chf(self) -> Optional[Decimal]:
        """``amount_out_of_range``: the smallest allowed payment, in CHF."""
        return _decimal_or_none(self.problem.get("minChf"))

    @property
    def max_chf(self) -> Optional[Decimal]:
        """``amount_out_of_range``: the largest allowed payment, in CHF."""
        return _decimal_or_none(self.problem.get("maxChf"))

    @property
    def amount_chf(self) -> Optional[Decimal]:
        """``amount_out_of_range``: the requested amount converted to CHF."""
        return _decimal_or_none(self.problem.get("amountChf"))


class QintWebhookSignatureError(QintError):
    """The webhook signature header did not match the computed HMAC."""
