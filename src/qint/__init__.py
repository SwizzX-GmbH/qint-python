"""Qint — official Python SDK for the Qint merchant payments API.

Quickstart::

    from qint import QintClient

    qint = QintClient("qk_live_...")
    intent = qint.create_intent(
        amount="49.90", currency="CHF", title="Order #1024", idempotency_key="order-1024"
    )
    print(intent.checkout_url)  # send the buyer here

See https://docs.qint.ch for the full API reference.
"""

from ._version import __version__
from .client import DEFAULT_BASE_URL, QintClient
from .errors import (
    AMOUNT_OUT_OF_RANGE,
    RATE_UNAVAILABLE,
    SETTLEMENT_ASSET_MISMATCH,
    QintApiError,
    QintConnectionError,
    QintError,
    QintWebhookSignatureError,
)
from .http import HttpResponse, Transport, UrllibTransport
from .models import (
    Currency,
    CurrencyAvailability,
    CurrencyList,
    Intent,
    IntentList,
    IntentStatus,
    PaymentStatusEvent,
    PingEvent,
    SettlementAsset,
)
from .webhooks import (
    EVENT_ID_HEADER,
    PAYMENT_STATUS_EVENT,
    PING_EVENT,
    SIGNATURE_HEADER,
    WebhookEvent,
    compute_signature,
    construct_event,
    parse_event,
    verify_webhook_signature,
)

__all__ = [
    "__version__",
    "DEFAULT_BASE_URL",
    "QintClient",
    "QintError",
    "QintApiError",
    "QintConnectionError",
    "QintWebhookSignatureError",
    "AMOUNT_OUT_OF_RANGE",
    "RATE_UNAVAILABLE",
    "SETTLEMENT_ASSET_MISMATCH",
    "Transport",
    "UrllibTransport",
    "HttpResponse",
    "Intent",
    "IntentList",
    "IntentStatus",
    "Currency",
    "PaymentStatusEvent",
    "PingEvent",
    "WebhookEvent",
    "SettlementAsset",
    "CurrencyAvailability",
    "CurrencyList",
    "verify_webhook_signature",
    "compute_signature",
    "parse_event",
    "construct_event",
    "SIGNATURE_HEADER",
    "EVENT_ID_HEADER",
    "PAYMENT_STATUS_EVENT",
    "PING_EVENT",
]
