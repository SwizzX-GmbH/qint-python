# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

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
