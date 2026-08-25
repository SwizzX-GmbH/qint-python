"""Client request-shaping tests. All offline via a recording fake transport."""

import json
from decimal import Decimal

import pytest

from qint import Currency, Intent, IntentList, IntentStatus, QintApiError, QintClient
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
