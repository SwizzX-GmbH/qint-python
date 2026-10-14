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


class SettlementAsset(str, Enum):
    """The stablecoin a merchant's balance is held in.

    Merchants registered in the European Union settle in ``USDC`` (USDT is not
    authorised under MiCA); all other merchants settle in ``USDT``.
    """

    USDT = "USDT"
    USDC = "USDC"

    def __str__(self) -> str:
        return self.value


def _to_settlement_asset(value: Any) -> Optional[Union[SettlementAsset, str]]:
    """Coerce a wire settlement asset, tolerating unknown values."""
    if value is None:
        return None
    try:
        return SettlementAsset(value)
    except ValueError:
        return str(value)


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
      credited, in ``currency`` — ``None`` until the payment is settled.
    - ``settled_amount``: what the execution partner booked as realised.
    - ``received_amount``: the fiat amount actually paid when the payment
      settled short within the merchant's accepted underpayment.
    - ``underpaid_bps``: how short, in basis points of the invoice.
    - ``credit_usdt`` / ``credit_rate``: the amount credited to the balance
      and the rate it was booked at (``currency`` units per 1 unit of
      ``credit_asset``). The name ``credit_usdt`` predates USDC: for a merchant
      settling in USDC the amount is USDC.
    - ``credit_asset``: the stablecoin the credit was booked in
      (:class:`SettlementAsset` — ``USDC`` for merchants registered in the EU,
      ``USDT`` otherwise); ``None`` until credited.
    - ``reversed`` / ``reversed_at``: set when the payment was reversed after
      settlement; the status stays ``settled`` but treat it as not paid.
    - ``underpaid``: the buyer sent less than the quoted crypto amount (a flag,
      not a status).
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
    credit_asset: Optional[Union[SettlementAsset, str]] = None
    reversed: bool = False
    underpaid: bool = False
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
            credit_asset=_to_settlement_asset(data.get("creditAsset")),
            reversed=bool(data.get("reversed") or data.get("reversedAt")),
            underpaid=bool(data.get("underpaid", False)),
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


@dataclass
class CurrencyAvailability:
    """One fiat currency and whether Qint offers it for new payments right now.

    ``code`` stays a plain string so currencies added later still parse.
    """

    code: str
    enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurrencyAvailability":
        return cls(code=str(data.get("code", "")), enabled=bool(data.get("enabled", False)))


@dataclass
class CurrencyList:
    """``GET /public/currencies`` — every fiat currency, in display order.

    Qint can switch a currency off (and back on) at any time; while it is off,
    creating an intent in it is refused with ``400``. Use :attr:`enabled_codes`
    to hide disabled currencies. The response is cacheable for 30 seconds.
    """

    currencies: List[CurrencyAvailability]
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurrencyList":
        return cls(
            currencies=[CurrencyAvailability.from_dict(c) for c in data.get("currencies", [])],
            raw=data,
        )

    @property
    def enabled_codes(self) -> List[str]:
        """The codes currently offered for new payments, in display order."""
        return [c.code for c in self.currencies if c.enabled]

    def is_enabled(self, code: Union["Currency", str]) -> bool:
        """Whether ``code`` (case-insensitive) is offered for new payments."""
        wanted = str(code).strip().upper()
        return any(c.enabled and c.code.upper() == wanted for c in self.currencies)

    def __iter__(self):
        return iter(self.currencies)

    def __len__(self) -> int:
        return len(self.currencies)


@dataclass
class PingEvent:
    """The ``ping`` test event (dashboard "Send test event"). Verify, return 2xx, ignore."""

    type: str
    endpoint_id: str = ""
    sent_at: str = ""
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PingEvent":
        return cls(
            type=data.get("type", "ping"),
            endpoint_id=str(data.get("endpointId") or ""),
            sent_at=str(data.get("sentAt") or ""),
            raw=data,
        )
