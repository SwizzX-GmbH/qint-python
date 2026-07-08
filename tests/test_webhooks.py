"""Webhook signature + parsing tests. Fully offline."""

import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from qint import (
    PaymentStatusEvent,
    QintWebhookSignatureError,
    compute_signature,
    construct_event,
    parse_event,
    verify_webhook_signature,
)

SECRET = "whsec_test_secret"

EVENT = {
    "type": "payment.status",
    "intentId": "pi_abc123",
    "status": "settled",
    "amount": 49.90,
    "currency": "CHF",
    "assetSymbol": "USDT",
    "invoiceId": "inv_1",
    "paymentLinkId": None,
    "occurredAt": "2026-07-08T10:15:00Z",
    "underpaid": False,
    "expectedCryptoAmount": "49.90000000",
    "receivedCryptoAmount": "49.90000000",
}


def raw() -> bytes:
    return json.dumps(EVENT).encode("utf-8")


def sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()


def test_valid_signature_passes():
    body = raw()
    assert verify_webhook_signature(body, sign(body), SECRET) is True


def test_valid_signature_accepts_str_body():
    body = raw()
    assert verify_webhook_signature(body.decode(), sign(body), SECRET) is True


def test_bare_hex_signature_accepted():
    body = raw()
    bare = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, bare, SECRET) is True


def test_tampered_body_fails():
    body = raw()
    header = sign(body)
    tampered = body + b" "
    assert verify_webhook_signature(tampered, header, SECRET) is False


def test_tampered_signature_fails():
    body = raw()
    header = sign(body)
    bad = header[:-1] + ("0" if header[-1] != "0" else "1")
    assert verify_webhook_signature(body, bad, SECRET) is False


def test_wrong_secret_fails():
    body = raw()
    assert verify_webhook_signature(body, sign(body), "whsec_wrong") is False


def test_wrong_scheme_fails():
    body = raw()
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, "sha1=" + digest, SECRET) is False


def test_empty_or_missing_inputs_fail():
    body = raw()
    assert verify_webhook_signature(body, "", SECRET) is False
    assert verify_webhook_signature(body, sign(body), "") is False


def test_compute_signature_matches_reference():
    body = raw()
    expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert compute_signature(body, SECRET) == expected


def test_parse_event_maps_all_fields():
    event = parse_event(raw())
    assert isinstance(event, PaymentStatusEvent)
    assert event.type == "payment.status"
    assert event.intent_id == "pi_abc123"
    assert str(event.status) == "settled"
    assert event.amount == Decimal("49.9")
    assert event.currency == "CHF"
    assert event.asset_symbol == "USDT"
    assert event.invoice_id == "inv_1"
    assert event.payment_link_id is None
    assert event.underpaid is False
    assert event.expected_crypto_amount == "49.90000000"
    assert event.received_crypto_amount == "49.90000000"


def test_construct_event_verifies_then_parses():
    body = raw()
    event = construct_event(body, sign(body), SECRET)
    assert event.intent_id == "pi_abc123"


def test_construct_event_raises_on_bad_signature():
    body = raw()
    with pytest.raises(QintWebhookSignatureError):
        construct_event(body, sign(body, "whsec_wrong"), SECRET)
