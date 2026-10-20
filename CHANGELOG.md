# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-10-20

Follows the Qint API change of 2026-10-20: the merchant balance is now held in
fiat, in the merchant's Account Currency, instead of a stablecoin.

### Breaking

- `Intent.credit_usdt` and `Intent.credit_asset` are **removed** (the API no
  longer sends `creditUsdt` / `creditAsset`).
- `Intent.credit_rate` keeps its name but **changes meaning**: it is now
  `credit_currency` units per 1 unit of the invoice `currency` (1 when they
  match). It used to be fiat per stablecoin unit.
- The `SettlementAsset` enum is removed.

### Added

- `Intent.credit_amount` (`Decimal`, 2 dp) and `Intent.credit_currency` (the
  Account Currency at quote time): what the payment added to the balance.
  `None` until credited and on payments settled before 2026-10-20.
- `PaymentStatusEvent.credit_amount`, `credit_currency` and `credit_rate`,
  filled on the `settled` event.

### Changed

- `SETTLEMENT_ASSET_MISMATCH` stays; it now concerns crypto payouts only.
- README: "Settlement asset" replaced by "Account Currency and the credit".

## [0.2.0] - 2026-10-14

### Added

- `QintClient.list_currencies()` → `CurrencyList` for the public
  `GET /api/v1/public/currencies`: every fiat currency with its `enabled` flag,
  plus `enabled_codes` and `is_enabled(code)`. Sent without the API key. Use it
  to hide currencies Qint has switched off; cache it for ~30 s.
- `SettlementAsset` enum (`USDT`, `USDC`) and `Intent.credit_asset` — the
  stablecoin the credit was booked in (USDC for merchants registered in the EU,
  USDT otherwise). Unknown values parse as plain strings.
- `Intent.reversed` and `Intent.underpaid` boolean flags (default `False`).
- `PingEvent` for the dashboard's `ping` test webhook (`endpoint_id`,
  `sent_at`); `PAYMENT_STATUS_EVENT` / `PING_EVENT` constants and the
  `WebhookEvent` union type.
- `SETTLEMENT_ASSET_MISMATCH` error-code constant (returned by the dashboard
  API's payout endpoints; listed for completeness).
- `QintApiError.trace_id` and `QintApiError.is_currency_disabled` (the plain
  `400` returned for a currency Qint has switched off).
- `GBP` is a supported currency (`Currency.GBP`); intents accept CHF, EUR, USD
  or GBP.
- Optional `Intent` fields: `fee_amount`, `net_amount`, `settled_amount`,
  `received_amount`, `underpaid_bps`, `credit_usdt`, `credit_rate`,
  `reversed_at` (all `None` when absent).
- Optional `PaymentStatusEvent` fields: `received_amount`, `underpaid_bps`,
  `reversed`, `reversed_at`.
- `QintApiError.code`, `.extensions`, and `.min_chf` / `.max_chf` /
  `.amount_chf`, plus the `AMOUNT_OUT_OF_RANGE` and `RATE_UNAVAILABLE`
  constants for the per-payment limit errors (`400 amount_out_of_range`,
  `503 rate_unavailable`).

### Changed

- `parse_event` / `construct_event` return a `PingEvent` for `type == "ping"`
  (previously a mostly-empty `PaymentStatusEvent`). Other unknown event types
  still parse as `PaymentStatusEvent` with the original JSON on `raw`.
- `Intent.credit_usdt` / `credit_rate` are documented as the amount and rate in
  `credit_asset` (the field name predates USDC). `fee_amount` / `net_amount`
  are `None` until the payment is settled.
- The distribution is named **`qint-sdk`** (`pip install qint-sdk` once it is
  on PyPI; not uploaded yet);
  `qint` on PyPI belongs to an unrelated project. The import name is unchanged
  (`from qint import QintClient`).

- **Breaking:** `create_intent` now requires `idempotency_key` (keyword-only).
  The API rejects intent creation without an idempotency key (`400`); omitting
  the argument raises `TypeError`, and a blank key raises `ValueError` before
  any request is sent.

## [0.1.0] - 2026-07-08

### Added

- `QintClient` with `create_intent`, `get_intent`, and `list_intents`.
- Typed models: `Intent`, `IntentList`, `PaymentStatusEvent`, plus the
  `IntentStatus` and `Currency` enums. Monetary amounts parse to `Decimal`.
- Typed errors: `QintError`, `QintApiError` (HTTP status + RFC 7807 `detail`),
  `QintConnectionError`, `QintWebhookSignatureError`.
- Webhook helpers: `verify_webhook_signature` (constant-time), `parse_event`,
  `construct_event`, and `compute_signature`.
- Pluggable HTTP `Transport` (stdlib `urllib` by default) for offline testing.
- `py.typed` marker; zero runtime dependencies; Python 3.8+.
