"""Typed models mirroring the Qint public API contract.

Models are plain :mod:`dataclasses` (no third-party dependencies). Each has a
``from_dict`` constructor that maps the API's camelCase JSON onto snake_case
Python attributes and ignores unknown keys so new server fields never break
older clients.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class IntentStatus(str, Enum):
    """Lifecycle status of a payment intent (lowercase wire values)."""

    INITIATED = "initiated"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SETTLED = "settled"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

    def __str__(self) -> str:  # so f-strings / urlencode emit the bare value
        return self.value


class Currency(str, Enum):
    """Fiat currencies accepted when creating an intent."""

    CHF = "CHF"
    EUR = "EUR"
    USD = "USD"

    def __str__(self) -> str:
        return self.value


def _to_status(value: Any) -> Union[IntentStatus, str]:
    """Coerce a wire status to :class:`IntentStatus`, tolerating unknown values."""
    if value is None:
        return value  # type: ignore[return-value]
    try:
        return IntentStatus(value)
    except ValueError:
        return str(value)


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class Intent:
    """A payment intent as returned by the API.

    ``amount`` is a :class:`~decimal.Decimal` (parsed without float rounding).
    ``crypto_amount`` is left as the API's 8-decimal-place string. Timestamps
    are ISO-8601 strings exactly as sent by the server.
    """

    id: str
    status: Union[IntentStatus, str]
    amount: Decimal
    currency: str
    checkout_url: str
    created_at: str
    expires_at: str
    title: Optional[str] = None
    asset_symbol: Optional[str] = None
    crypto_amount: Optional[str] = None
    deposit_address: Optional[str] = None
    return_url: Optional[str] = None
    confirmed_at: Optional[str] = None
    settled_at: Optional[str] = None
    #: The untouched JSON object the server returned, for forward compatibility.
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        return cls(
            id=data["id"],
            status=_to_status(data.get("status")),
            amount=_to_decimal(data.get("amount")) or Decimal("0"),
            currency=data.get("currency", ""),
            checkout_url=data.get("checkoutUrl", ""),
            created_at=data.get("createdAt", ""),
            expires_at=data.get("expiresAt", ""),
            title=data.get("title"),
            asset_symbol=data.get("assetSymbol"),
            crypto_amount=data.get("cryptoAmount"),
            deposit_address=data.get("depositAddress"),
            return_url=data.get("returnUrl"),
            confirmed_at=data.get("confirmedAt"),
            settled_at=data.get("settledAt"),
            raw=data,
        )


@dataclass
class IntentList:
    """A single page of intents from ``GET /intents``."""

    items: List[Intent]
    total: int
    page: int
    page_size: int
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentList":
        return cls(
            items=[Intent.from_dict(i) for i in data.get("items", [])],
            total=int(data.get("total", 0)),
            page=int(data.get("page", 1)),
            page_size=int(data.get("pageSize", 0)),
            raw=data,
        )

    def __iter__(self):  # allow `for intent in page:`
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


@dataclass
class PaymentStatusEvent:
    """A ``payment.status`` webhook event payload."""

    type: str
    intent_id: str
    status: Union[IntentStatus, str]
    amount: Decimal
    currency: str
    asset_symbol: Optional[str] = None
    invoice_id: Optional[str] = None
    payment_link_id: Optional[str] = None
    occurred_at: str = ""
    underpaid: Optional[bool] = None
    expected_crypto_amount: Optional[str] = None
    received_crypto_amount: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaymentStatusEvent":
        return cls(
            type=data.get("type", ""),
            intent_id=data.get("intentId", ""),
            status=_to_status(data.get("status")),
            amount=_to_decimal(data.get("amount")) or Decimal("0"),
            currency=data.get("currency", ""),
            asset_symbol=data.get("assetSymbol"),
            invoice_id=data.get("invoiceId"),
            payment_link_id=data.get("paymentLinkId"),
            occurred_at=data.get("occurredAt", ""),
            underpaid=data.get("underpaid"),
            expected_crypto_amount=data.get("expectedCryptoAmount"),
            received_crypto_amount=data.get("receivedCryptoAmount"),
            raw=data,
        )
