# Qint Python SDK

A small, typed, dependency-free Python client for the [Qint](https://qint.ch)
merchant payments API. Create payment intents, send buyers to hosted checkout,
read intent status, and verify webhooks.

Full API reference: **https://docs.qint.ch**

## Install

```bash
pip install qint-sdk
```

Until the first PyPI release is published, install from git:

```bash
pip install "git+https://github.com/SwizzX-GmbH/qint-python.git@v0.3.0"
```

> **⚠️ Do not run `pip install qint`.** That installs a **different, unrelated
> package** — `qint` on PyPI is *"Quantized Integer type in Python!"* by Neural
> Dynamics, not this SDK. The distribution name of this SDK is **`qint-sdk`**;
> see [`PUBLISH.md`](./PUBLISH.md).
>
> The **import** name is `qint` regardless: `from qint import QintClient`.

Requires Python 3.8+. No third-party runtime dependencies — the client is built
on the standard library.

## 30-second quickstart

```python
from qint import QintClient

qint = QintClient("qk_live_...")  # your API key (needs the Write scope)

# 1. Create a payment intent
intent = qint.create_intent(
    amount="49.90",
    currency="CHF",
    idempotency_key="order-1024",  # required — unique per merchant; safe to retry
    title="Order #1024",
    return_url="https://shop.example/thanks",
)

# 2. Send the buyer to hosted checkout
print(intent.checkout_url)  # -> redirect the customer here

# 3a. Poll for status (or, better, receive a webhook — see below)
latest = qint.get_intent(intent.id)
print(latest.status)  # IntentStatus.PENDING, .CONFIRMED, .SETTLED, ...
```

The default base URL is `https://api.qint.ch/api/v1`; override it via the
constructor (`QintClient(key, base_url=...)`) if you need to.

## Client API

```python
QintClient(
    api_key: str,
    *,
    base_url: str = "https://api.qint.ch/api/v1",
    timeout: float = 30.0,
    transport: Transport | None = None,
)

client.create_intent(
    amount,                       # int | float | str | Decimal (major units)
    currency,                     # "CHF" | "EUR" | "USD" | "GBP" or qint.Currency
    *,
    idempotency_key: str,         # required — unique per merchant (e.g. your order id)
    title: str | None = None,
    return_url: str | None = None,
) -> Intent

client.get_intent(intent_id: str) -> Intent

client.list_intents(
    *,
    status=None,                  # "pending" | ... or qint.IntentStatus
    page: int | None = None,
    page_size: int | None = None,
) -> IntentList                    # .items, .total, .page, .page_size (iterable)

client.list_currencies() -> CurrencyList   # public, sent without the API key
```

### Currencies

Intents accept `CHF`, `EUR`, `USD` and `GBP` — but only while Qint offers the
currency. Qint can switch a currency off (and back on) at any time; while it is
off, `create_intent` in that currency fails with a plain `400` (see
[Errors](#errors)). `list_currencies()` calls the public
`GET /api/v1/public/currencies` so you can hide disabled currencies:

```python
currencies = qint.list_currencies()
print(currencies.enabled_codes)        # e.g. ["CHF", "EUR", "USD", "GBP"]
if not currencies.is_enabled("GBP"):
    ...                                # don't offer GBP at checkout
for c in currencies:                   # CurrencyAvailability(code, enabled)
    print(c.code, c.enabled)
```

The response is cacheable for 30 seconds — cache it on your side rather than
calling it on every checkout. `code` is a plain string, so currencies added
later parse without an SDK update.

`Intent` fields: `id`, `status` (an `IntentStatus`), `amount` (a `Decimal`,
parsed without float rounding), `currency`, `title`, `asset_symbol`,
`crypto_amount` (8-dp string), `deposit_address`, `checkout_url`, `return_url`,
`created_at`, `expires_at`, `confirmed_at`, `settled_at`, the flags `reversed`
and `underpaid` (`bool`), plus the optional `reversed_at`, `fee_amount`,
`net_amount`, `settled_amount`, `received_amount`, `underpaid_bps`,
`credit_amount`, `credit_currency` and `credit_rate` (each `None` until known — fee
and net only once the payment is settled), plus `raw` (the untouched JSON).
Unknown response fields are ignored, so new server fields never break you.

### Account Currency and the credit

Your balance is held in fiat, in your **Account Currency** (CHF by default;
EUR, USD or GBP are possible). The amount a payment adds to it is fixed when the
buyer is quoted, never by a rate read at settlement. Once a payment is credited,
`intent.credit_amount` is the amount added to your balance (a `Decimal`, 2
decimal places), `intent.credit_currency` the currency it is in (your Account
Currency at quote time) and `intent.credit_rate` the `credit_currency` units per
1 unit of the invoice `currency` (`1` when they match). All three are `None`
until credited, and stay `None` on payments settled before the fiat balance
(20 October 2026). The `payment.status` webhook (`PaymentStatusEvent`) carries
the same three fields, filled on the `settled` event.

Statuses: `initiated`, `pending`, `confirmed`, `settled`, `failed`, `expired`,
`cancelled`.

## Errors

Any non-2xx response raises `QintApiError`, which carries the HTTP status, the
RFC 7807 problem-details message and, when the API sends one, a machine-readable
`code`:

```python
from qint import QintApiError

try:
    qint.create_intent(amount="10.00", currency="CHF", idempotency_key="order-10")
except QintApiError as e:
    print(e.status_code)  # e.g. 403
    print(e.detail)       # e.g. "This API key lacks the Write scope."
    print(e.code)         # e.g. "amount_out_of_range", or None
    print(e.trace_id)     # request correlation id — quote it to support
    print(e.problem)      # full problem+json dict
```

Known codes are exported as constants: `AMOUNT_OUT_OF_RANGE`,
`RATE_UNAVAILABLE` and `SETTLEMENT_ASSET_MISMATCH` (the last one concerns
crypto payouts only and is returned by the dashboard's payout endpoints, not the
merchant API — listed for completeness). Treat `code` as an open set.

### Disabled currencies

Creating an intent in a currency Qint has switched off fails with a `400`
without a `code`; `e.detail` reads e.g. *"GBP is currently disabled on Qint.
currency must be one of: CHF, EUR, USD."* and `e.is_currency_disabled` is
`True`. Check `list_currencies()` before offering a currency.

### Payment limits

Each payment must be between CHF 10 and CHF 100'000 (or the equivalent in EUR,
USD or GBP; a merchant may have an individually agreed cap). Outside that range `create_intent` raises a `400` with
`e.code == qint.AMOUNT_OUT_OF_RANGE` (`"amount_out_of_range"`) and the numbers
on `e.min_chf`, `e.max_chf` and `e.amount_chf` (`Decimal`). If no exchange rate
is available to judge a non-CHF amount it raises a `503` with
`e.code == qint.RATE_UNAVAILABLE` (`"rate_unavailable"`) — retry in a minute.
Every non-standard problem member is also in `e.extensions`.

### Underpaid payments

A payment that comes up short but within your accepted underpayment still
settles. The `payment.status` webhook then carries `underpaid=True`,
`received_amount` (the fiat amount actually paid, in the intent's currency) and
`underpaid_bps` (how short, in basis points of the invoice); both are `None`
otherwise. `Intent` declares the same two fields plus the fee, credit and
reversal fields listed above. `reversed=True` (with `reversed_at`) means the
payment was reversed after settlement: treat it as not paid even though its
status stays `settled`.

Network-level failures (DNS/TLS/timeout) raise `QintConnectionError`. Both derive
from `QintError`.

## Webhooks

Configure a webhook endpoint in the Qint dashboard; you receive a signing secret
(`whsec_...`). Each delivery is a JSON `POST` with these headers:

- `X-Qint-Signature: sha256=<hex HMAC-SHA256 of the raw body>`
- `X-Qint-Event-Id: <id>` — a stable id for **deduplication**

Verify against the **raw request body** (not re-serialized JSON), then handle the
event. Acknowledge with a `2xx` quickly and do slow work out of band.

```python
from qint import verify_webhook_signature, parse_event, construct_event

# Flask example
@app.post("/webhooks/qint")
def qint_webhook():
    raw_body = request.get_data()                     # RAW bytes
    signature = request.headers.get("X-Qint-Signature", "")
    event_id = request.headers.get("X-Qint-Event-Id", "")

    if not verify_webhook_signature(raw_body, signature, WHSEC_SECRET):
        return ("bad signature", 400)

    if already_processed(event_id):                   # dedupe on X-Qint-Event-Id
        return ("", 200)

    event = parse_event(raw_body)
    if event.type == "payment.status" and str(event.status) == "settled":
        if event.reversed:
            undo_fulfilment(event.intent_id)          # reversed after settlement
        else:
            fulfill_order(event.intent_id)
    # "ping" (dashboard "Send test event") parses to a PingEvent; any other,
    # future event type: ignore it and still answer 2xx.

    mark_processed(event_id)
    return ("", 200)                                  # ack fast
```

`construct_event(raw_body, signature, secret)` is a one-liner that verifies and
parses in one step, raising `QintWebhookSignatureError` on a bad signature.

The signature check uses `hmac.compare_digest` (constant-time).

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The client accepts a custom `transport=`, so tests run fully offline with no
network access.

## License

MIT © SwizzX GmbH — see [`LICENSE`](./LICENSE).
