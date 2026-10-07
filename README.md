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
pip install "git+https://github.com/SwizzX-GmbH/qint-python.git@v0.1.0"
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

The default base URL is `https://api.qint.ch/api/v1`. Override it via the
constructor (`QintClient(key, base_url="https://api.qint.ch/api/v1")`) once the
`api.qint.ch` hostname is live.

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
    currency,                     # "CHF" | "EUR" | "USD" or qint.Currency
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
```

`Intent` fields: `id`, `status` (an `IntentStatus`), `amount` (a `Decimal`,
parsed without float rounding), `currency`, `title`, `asset_symbol`,
`crypto_amount` (8-dp string), `deposit_address`, `checkout_url`, `return_url`,
`created_at`, `expires_at`, `confirmed_at`, `settled_at`, plus `raw` (the
untouched JSON).

Statuses: `initiated`, `pending`, `confirmed`, `settled`, `failed`, `expired`,
`cancelled`.

## Errors

Any non-2xx response raises `QintApiError`, which carries the HTTP status and the
RFC 7807 problem-details message:

```python
from qint import QintApiError

try:
    qint.create_intent(amount="10.00", currency="CHF", idempotency_key="order-10")
except QintApiError as e:
    print(e.status_code)  # e.g. 403
    print(e.detail)       # e.g. "This API key lacks the Write scope."
    print(e.problem)      # full problem+json dict
```

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
        fulfill_order(event.intent_id)

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
