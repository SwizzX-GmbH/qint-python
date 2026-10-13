# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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

- The distribution is now published as **`qint-sdk`** (`pip install qint-sdk`);
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
