"""Client request-shaping tests. All offline via a recording fake transport."""

import json
from decimal import Decimal

import pytest

from qint import (
    AMOUNT_OUT_OF_RANGE,
    RATE_UNAVAILABLE,
    SETTLEMENT_ASSET_MISMATCH,
    Currency,
    CurrencyList,
    SettlementAsset,
    __version__,
    Intent,
    IntentList,
    IntentStatus,
    QintApiError,
    QintClient,
)
from qint.http import HttpResponse


class FakeTransport:
    """Records the last request and replays a canned response."""

    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body if body is not None else {}
        self.calls = []

    def request(self, method, url, *, headers, body=None, timeout=30.0):
        parsed_body = json.loads(body.decode("utf-8")) if body else None
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": parsed_body,
                "timeout": timeout,
            }
        )
        payload = json.dumps(self.body).encode("utf-8")
        return HttpResponse(
            status=self.status,
            body=payload,
            headers={"content-type": "application/problem+json"},
        )

    @property
    def last(self):
        return self.calls[-1]


INTENT_JSON = {
    "id": "pi_abc123",
    "status": "pending",
    "amount": 49.90,
    "currency": "CHF",
    "title": "Order #1024",
    "assetSymbol": "USDT",
    "cryptoAmount": "49.90000000",
    "depositAddress": "0xdeadbeef",
    "checkoutUrl": "https://checkout.qint.ch/pi_abc123",
    "returnUrl": "https://shop.example/thanks",
    "createdAt": "2026-07-08T10:00:00Z",
    "expiresAt": "2026-07-08T10:30:00Z",
}


def make_client(transport):
    return QintClient("qk_live_test", transport=transport)


def test_create_intent_shapes_request():
    t = FakeTransport(status=201, body=INTENT_JSON)
    client = make_client(t)

    intent = client.create_intent(
        amount="49.90",
        currency=Currency.CHF,
        title="Order #1024",
        idempotency_key="idem-1",
        return_url="https://shop.example/thanks",
    )

    call = t.last
    assert call["method"] == "POST"
    assert call["url"] == "https://api.qint.ch/api/v1/intents"
    assert call["headers"]["Authorization"] == "Bearer qk_live_test"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["headers"]["Accept"] == "application/json"
    assert call["headers"]["User-Agent"].startswith("qint-python/")
    # body uses the API's camelCase keys and a JSON *number* amount
    assert call["body"] == {
        "amount": 49.9,
        "currency": "CHF",
        "title": "Order #1024",
        "idempotencyKey": "idem-1",
        "returnUrl": "https://shop.example/thanks",
    }

    assert isinstance(intent, Intent)
    assert intent.id == "pi_abc123"
    assert intent.status is IntentStatus.PENDING
    assert intent.amount == Decimal("49.90")  # parsed exact, no float rounding
    assert intent.checkout_url == "https://checkout.qint.ch/pi_abc123"
    assert intent.crypto_amount == "49.90000000"


def test_create_intent_omits_optional_fields():
    t = FakeTransport(status=201, body=INTENT_JSON)
    client = make_client(t)

    client.create_intent(amount=100, currency="EUR", idempotency_key="order-100")

    assert t.last["body"] == {
        "amount": 100,
        "currency": "EUR",
        "idempotencyKey": "order-100",
    }


def test_create_intent_requires_idempotency_key():
    t = FakeTransport(status=201, body=INTENT_JSON)
    client = make_client(t)

    # omitted entirely -> TypeError (missing required keyword-only argument)
    with pytest.raises(TypeError):
        client.create_intent(amount=100, currency="EUR")  # type: ignore[call-arg]
    # blank -> ValueError, and no request is sent either way
    with pytest.raises(ValueError, match="idempotency_key"):
        client.create_intent(amount=100, currency="EUR", idempotency_key="  ")

    assert t.calls == []


def test_create_intent_integer_amount_stays_integer():
    t = FakeTransport(status=201, body=INTENT_JSON)
    client = make_client(t)

    client.create_intent(amount=Decimal("50.00"), currency="USD", idempotency_key="order-50")

    assert t.last["body"]["amount"] == 50
    assert isinstance(t.last["body"]["amount"], int)


def test_get_intent_path_and_method():
    t = FakeTransport(status=200, body=INTENT_JSON)
    client = make_client(t)

    client.get_intent("pi_abc123")

    assert t.last["method"] == "GET"
    assert t.last["url"] == "https://api.qint.ch/api/v1/intents/pi_abc123"
    assert t.last["body"] is None


def test_list_intents_query_params():
    t = FakeTransport(
        status=200,
        body={"items": [INTENT_JSON], "total": 1, "page": 2, "pageSize": 25},
    )
    client = make_client(t)

    result = client.list_intents(status=IntentStatus.SETTLED, page=2, page_size=25)

    url = t.last["url"]
    assert url.startswith("https://api.qint.ch/api/v1/intents?")
    assert "status=settled" in url
    assert "page=2" in url
    assert "pageSize=25" in url

    assert isinstance(result, IntentList)
    assert result.total == 1
    assert result.page == 2
    assert result.page_size == 25
    assert len(result) == 1
    assert result.items[0].id == "pi_abc123"


def test_list_intents_without_params_has_no_query():
    t = FakeTransport(status=200, body={"items": [], "total": 0, "page": 1, "pageSize": 20})
    client = make_client(t)

    client.list_intents()

    assert t.last["url"] == "https://api.qint.ch/api/v1/intents"


def test_custom_base_url_is_respected():
    # A base DISTINCT from the default — this test is vacuous otherwise.
    t = FakeTransport(status=201, body=INTENT_JSON)
    client = QintClient("qk_live_x", base_url="https://api.example.test/v1/", transport=t)

    client.create_intent(amount=10, currency="CHF", idempotency_key="order-10")

    # trailing slash normalised, no double slash
    assert t.last["url"] == "https://api.example.test/v1/intents"


def test_non_2xx_raises_typed_api_error_with_detail():
    problem = {
        "type": "about:blank",
        "title": "Forbidden",
        "status": 403,
        "detail": "This API key lacks the Write scope.",
    }
    t = FakeTransport(status=403, body=problem)
    client = make_client(t)

    with pytest.raises(QintApiError) as excinfo:
        client.create_intent(amount=10, currency="CHF", idempotency_key="order-10")

    err = excinfo.value
    assert err.status_code == 403
    assert err.detail == "This API key lacks the Write scope."
    assert err.title == "Forbidden"
    assert "403" in str(err)


def test_missing_api_key_raises():
    with pytest.raises(ValueError):
        QintClient("")


def test_bool_amount_rejected():
    client = make_client(FakeTransport(status=201, body=INTENT_JSON))
    with pytest.raises(TypeError):
        client.create_intent(amount=True, currency="CHF", idempotency_key="order-x")


def test_gbp_is_a_supported_currency():
    assert [c.value for c in Currency] == ["CHF", "EUR", "USD", "GBP"]
    t = FakeTransport(status=201, body={**INTENT_JSON, "currency": "GBP"})
    client = make_client(t)

    intent = client.create_intent(amount="25.00", currency=Currency.GBP, idempotency_key="order-gbp")

    assert t.last["body"]["currency"] == "GBP"
    assert intent.currency == "GBP"


def test_intent_parses_fee_underpayment_and_reversal_fields():
    body = {
        **INTENT_JSON,
        "status": "settled",
        "amount": 100.00,
        "settledAt": "2026-07-08T10:20:00Z",
        "feeAmount": 0.98,
        "netAmount": 97.02,
        "settledAmount": None,
        "receivedAmount": 98.00,
        "underpaidBps": 200,
        "creditUsdt": 108.9,
        "creditRate": 0.8909,
        "reversedAt": "2026-07-09T09:00:00Z",
    }
    client = make_client(FakeTransport(status=200, body=body))

    intent = client.get_intent("pi_abc123")

    assert intent.fee_amount == Decimal("0.98")
    assert intent.net_amount == Decimal("97.02")
    assert intent.settled_amount is None
    assert intent.received_amount == Decimal("98.00")
    assert intent.underpaid_bps == 200
    assert intent.credit_usdt == Decimal("108.9")
    assert intent.credit_rate == Decimal("0.8909")
    assert intent.reversed_at == "2026-07-09T09:00:00Z"


def test_intent_without_new_fields_leaves_them_none():
    client = make_client(FakeTransport(status=200, body=INTENT_JSON))

    intent = client.get_intent("pi_abc123")

    assert intent.fee_amount is None
    assert intent.net_amount is None
    assert intent.settled_amount is None
    assert intent.received_amount is None
    assert intent.underpaid_bps is None
    assert intent.credit_usdt is None
    assert intent.credit_rate is None
    assert intent.reversed_at is None


def test_amount_out_of_range_exposes_code_and_limits():
    problem = {
        "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
        "title": "Amount out of range",
        "status": 400,
        "detail": "Payments must be between CHF 10 and CHF 100'000 (or the equivalent). This amount is CHF 5.00.",
        "traceId": "00-abc-def-00",
        "code": "amount_out_of_range",
        "minChf": 10,
        "maxChf": 100000,
        "amountChf": 5.00,
    }
    client = make_client(FakeTransport(status=400, body=problem))

    with pytest.raises(QintApiError) as excinfo:
        client.create_intent(amount="5.00", currency="CHF", idempotency_key="order-5")

    err = excinfo.value
    assert err.status_code == 400
    assert err.code == AMOUNT_OUT_OF_RANGE == "amount_out_of_range"
    assert err.min_chf == Decimal("10")
    assert err.max_chf == Decimal("100000")
    assert err.amount_chf == Decimal("5")
    assert err.extensions == {
        "traceId": "00-abc-def-00",
        "code": "amount_out_of_range",
        "minChf": 10,
        "maxChf": 100000,
        "amountChf": 5.00,
    }
    assert err.detail == (
        "Payments must be between CHF 10 and CHF 100'000 (or the equivalent). This amount is CHF 5.00."
    )


def test_rate_unavailable_exposes_code():
    problem = {
        "title": "Exchange rate unavailable",
        "status": 503,
        "detail": "Exchange rate unavailable — try again in a minute.",
        "code": "rate_unavailable",
    }
    client = make_client(FakeTransport(status=503, body=problem))

    with pytest.raises(QintApiError) as excinfo:
        client.create_intent(amount="50.00", currency="GBP", idempotency_key="order-50")

    err = excinfo.value
    assert err.status_code == 503
    assert err.code == RATE_UNAVAILABLE
    assert err.min_chf is None


def test_api_error_without_code_has_none():
    client = make_client(FakeTransport(status=404, body={"title": "Not Found", "status": 404}))

    with pytest.raises(QintApiError) as excinfo:
        client.get_intent("pi_missing")

    assert excinfo.value.code is None
    assert excinfo.value.extensions == {}


# -- 2026-10-14 API sync: currencies, settlement asset, flags, codes --------


def test_list_currencies_is_public_get_and_parses():
    t = FakeTransport(
        status=200,
        body={
            "currencies": [
                {"code": "CHF", "enabled": True},
                {"code": "EUR", "enabled": True},
                {"code": "USD", "enabled": True},
                {"code": "GBP", "enabled": False},
                {"code": "JPY", "enabled": True, "futureField": 1},
            ]
        },
    )
    client = make_client(t)

    currencies = client.list_currencies()

    assert t.last["method"] == "GET"
    assert t.last["url"] == "https://api.qint.ch/api/v1/public/currencies"
    assert "Authorization" not in t.last["headers"]
    assert t.last["body"] is None
    assert isinstance(currencies, CurrencyList)
    assert len(currencies) == 5
    assert currencies.enabled_codes == ["CHF", "EUR", "USD", "JPY"]
    assert currencies.is_enabled("chf")
    assert currencies.is_enabled(Currency.EUR)
    assert not currencies.is_enabled(Currency.GBP)
    assert not currencies.is_enabled("XYZ")
    assert [c.code for c in currencies] == ["CHF", "EUR", "USD", "GBP", "JPY"]


def test_list_currencies_empty_body_is_empty_list():
    client = make_client(FakeTransport(status=200, body={}))
    assert client.list_currencies().enabled_codes == []


def test_intent_parses_credit_asset_and_flags():
    data = dict(
        INTENT_JSON,
        status="settled",
        reversed=False,
        underpaid=True,
        feeAmount=0.25,
        netAmount=49.65,
        creditUsdt=55.123456,
        creditRate=0.9007,
        creditAsset="USDC",
    )
    intent = Intent.from_dict(data)
    assert intent.credit_asset is SettlementAsset.USDC
    assert intent.credit_usdt == Decimal("55.123456")
    assert intent.underpaid is True
    assert intent.reversed is False
    assert intent.fee_amount == Decimal("0.25")
    assert intent.net_amount == Decimal("49.65")


def test_intent_unknown_credit_asset_and_unknown_fields_tolerated():
    intent = Intent.from_dict(dict(INTENT_JSON, creditAsset="EURC", brandNew={"x": 1}))
    assert intent.credit_asset == "EURC"
    assert intent.raw["brandNew"] == {"x": 1}


def test_intent_null_fee_and_credit_until_settled():
    data = dict(
        INTENT_JSON,
        reversed=False,
        underpaid=False,
        feeAmount=None,
        netAmount=None,
        creditUsdt=None,
        creditRate=None,
        creditAsset=None,
    )
    intent = Intent.from_dict(data)
    assert intent.fee_amount is None
    assert intent.net_amount is None
    assert intent.credit_asset is None
    assert intent.reversed is False
    assert intent.underpaid is False


def test_intent_reversed_flag_and_defaults():
    reversed_intent = Intent.from_dict(
        dict(INTENT_JSON, status="settled", reversed=True, reversedAt="2026-07-08T11:00:00Z")
    )
    assert reversed_intent.reversed is True
    # older payloads without the flag: derived from reversedAt, else False
    legacy = Intent.from_dict(dict(INTENT_JSON, reversedAt="2026-07-08T11:00:00Z"))
    assert legacy.reversed is True
    plain = Intent.from_dict(INTENT_JSON)
    assert plain.reversed is False and plain.underpaid is False


def test_settlement_asset_values():
    assert [a.value for a in SettlementAsset] == ["USDT", "USDC"]
    assert str(SettlementAsset.USDC) == "USDC"


def test_disabled_currency_surfaces_400_and_detail():
    detail = "GBP is currently disabled on Qint. currency must be one of: CHF, EUR, USD."
    problem = {
        "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
        "title": "An error occurred while processing your request.",
        "status": 400,
        "detail": detail,
        "traceId": "00-abc-def-00",
    }
    client = make_client(FakeTransport(status=400, body=problem))

    with pytest.raises(QintApiError) as excinfo:
        client.create_intent(amount=50, currency=Currency.GBP, idempotency_key="order-gbp")

    err = excinfo.value
    assert err.status_code == 400
    assert err.detail == detail
    assert err.code is None
    assert err.is_currency_disabled is True
    assert err.trace_id == "00-abc-def-00"
    assert detail in str(err)


def test_other_400_is_not_currency_disabled():
    problem = {"status": 400, "detail": "currency must be one of: CHF, EUR, USD, GBP."}
    client = make_client(FakeTransport(status=400, body=problem))
    with pytest.raises(QintApiError) as excinfo:
        client.create_intent(amount=50, currency="JPY", idempotency_key="order-jpy")
    assert excinfo.value.is_currency_disabled is False
    assert excinfo.value.trace_id is None


def test_settlement_asset_mismatch_code_constant():
    assert SETTLEMENT_ASSET_MISMATCH == "settlement_asset_mismatch"
    problem = {
        "title": "Wrong payout asset",
        "status": 400,
        "detail": "Crypto payouts must be in your settlement asset (USDC).",
        "code": "settlement_asset_mismatch",
    }
    client = make_client(FakeTransport(status=400, body=problem))
    with pytest.raises(QintApiError) as excinfo:
        client.get_intent("pi_x")
    assert excinfo.value.code == SETTLEMENT_ASSET_MISMATCH


def test_user_agent_carries_version():
    t = FakeTransport(status=200, body=INTENT_JSON)
    make_client(t).get_intent("pi_abc123")
    assert t.last["headers"]["User-Agent"] == f"qint-python/{__version__}"
    assert __version__ == "0.2.0"
