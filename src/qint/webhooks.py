"""Webhook signature verification and event parsing.

Qint signs each delivery with ``X-Qint-Signature: sha256=<hex>`` where the hex
is ``HMAC-SHA256(raw_request_body, whsec_secret)``. Always verify against the
*raw* bytes of the request body — re-serialising the parsed JSON will change the
bytes and the signature will not match.

Every delivery also carries ``X-Qint-Event-Id``. Persist processed event ids and
skip duplicates: Qint may retry a delivery, and endpoints should be idempotent.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Union

from .errors import QintWebhookSignatureError
from .models import PaymentStatusEvent

SIGNATURE_HEADER = "X-Qint-Signature"
EVENT_ID_HEADER = "X-Qint-Event-Id"

_SCHEME = "sha256"


def _as_bytes(value: Union[str, bytes, bytearray]) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)


def compute_signature(raw_body: Union[str, bytes, bytearray], secret: str) -> str:
    """Return the hex HMAC-SHA256 of ``raw_body`` keyed by ``secret``."""
    return hmac.new(
        _as_bytes(secret), _as_bytes(raw_body), hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(
    raw_body: Union[str, bytes, bytearray],
    signature_header: str,
    secret: str,
) -> bool:
    """Constant-time check of an ``X-Qint-Signature`` header.

    Accepts either the full ``sha256=<hex>`` header value or a bare hex digest.
    Returns ``True`` only when the header matches ``HMAC-SHA256(raw_body, secret)``.
    Never raises on a bad/missing signature — it just returns ``False``.
    """
    if not signature_header or not secret:
        return False

    provided = signature_header.strip()
    if "=" in provided:
        scheme, _, value = provided.partition("=")
        if scheme.strip().lower() != _SCHEME:
            return False
        provided = value.strip()

    expected = compute_signature(raw_body, secret)
    # compare_digest is constant-time; ASCII-lowercase both hex strings first.
    return hmac.compare_digest(expected.lower(), provided.lower())


def parse_event(raw_body: Union[str, bytes, bytearray]) -> PaymentStatusEvent:
    """Parse a raw webhook body into a :class:`PaymentStatusEvent`.

    This does NOT verify the signature — call :func:`verify_webhook_signature`
    first (or use :func:`construct_event`).
    """
    data = json.loads(_as_bytes(raw_body).decode("utf-8"))
    return PaymentStatusEvent.from_dict(data)


def construct_event(
    raw_body: Union[str, bytes, bytearray],
    signature_header: str,
    secret: str,
) -> PaymentStatusEvent:
    """Verify the signature and return the parsed event, or raise.

    Raises:
        QintWebhookSignatureError: if the signature does not match.
    """
    if not verify_webhook_signature(raw_body, signature_header, secret):
        raise QintWebhookSignatureError("Webhook signature verification failed")
    return parse_event(raw_body)
