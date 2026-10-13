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
    """Fiat currencies accepted when creating an intent: CHF, EUR, USD or GBP."""

    CHF = "CHF"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"

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


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


@dataclass
class Intent:
    """A payment intent as returned by the API.

    ``amount`` is a :class:`~decimal.Decimal` (parsed without float rounding).
    ``crypto_amount`` is left as the API's 8-decimal-place string. Timestamps
    are ISO-8601 strings exactly as sent by the server.

    The fee, credit, underpayment and reversal fields are optional: each is
    ``None`` when the response does not include it.

    - ``fee_amount`` / ``net_amount``: Qint's fee and what the merchant is
      credited once the payment settles, in ``currency``.
    - ``settled_amount``: what the execution partner booked as realised.
    - ``received_amount``: the fiat amount actually paid when the payment
      settled short within the merchant's accepted underpayment.
    - ``underpaid_bps``: how short, in basis points of the invoice.
    - ``credit_usdt`` / ``credit_rate``: the USDT credited and the rate it was
      booked at (fiat per 1 USDT).
    - ``reversed_at``: set when the payment was reversed after settlement; the
      status stays ``settled`` but treat it as not paid.
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
    reversed_at: Optional[str] = None
    fee_amount: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    settled_amount: Optional[Decimal] = None
    received_amount: Optional[Decimal] = None
    underpaid_bps: Optional[int] = None
    credit_usdt: Optional[Decimal] = None
    credit_rate: Optional[Decimal] = None
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
            reversed_at=data.get("reversedAt"),
            fee_amount=_to_decimal(data.get("feeAmount")),
            net_amount=_to_decimal(data.get("netAmount")),
            settled_amount=_to_decimal(data.get("settledAmount")),
            received_amount=_to_decimal(data.get("receivedAmount")),
            underpaid_bps=_to_int(data.get("underpaidBps")),
            credit_usdt=_to_decimal(data.get("creditUsdt")),
            credit_rate=_to_decimal(data.get("creditRate")),
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
    """A ``payment.status`` webhook event payload.

    ``received_amount`` (fiat actually paid, in ``currency``) and
    ``underpaid_bps`` (how short, in basis points of the invoice) are set when
    the payment settled short within the merchant's accepted underpayment, and
    ``None`` otherwise. ``expected_crypto_amount`` / ``received_crypto_amount``
    are 8-decimal-place strings. ``reversed`` / ``reversed_at`` flag a payment
    reversed after settlement.
    """

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
    received_amount: Optional[Decimal] = None
    underpaid_bps: Optional[int] = None
    reversed: Optional[bool] = None
    reversed_at: Optional[str] = None
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
            received_amount=_to_decimal(data.get("receivedAmount")),
            underpaid_bps=_to_int(data.get("underpaidBps")),
            reversed=data.get("reversed"),
            reversed_at=data.get("reversedAt"),
            raw=data,
        )
