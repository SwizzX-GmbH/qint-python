"""The synchronous Qint API client."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from urllib.parse import quote, urlencode

from ._version import __version__
from .errors import QintApiError
from .http import HttpResponse, Transport, UrllibTransport
from .models import Currency, Intent, IntentList, IntentStatus

DEFAULT_BASE_URL = "https://api.qint.ch/api/v1"
DEFAULT_TIMEOUT = 30.0

AmountLike = Union[int, float, str, Decimal]
CurrencyLike = Union[Currency, str]
StatusLike = Union[IntentStatus, str]


def _amount_to_json(amount: AmountLike) -> Union[int, float]:
    """Normalise an amount to a JSON number.

    ``Decimal``/``str`` inputs are validated and emitted as a number so the
    server binds them to its decimal field (a JSON *string* would be rejected).
    Python's shortest-round-tripping float repr recovers currency values exactly.
    """
    if isinstance(amount, bool):  # bool is an int subclass — reject it explicitly
        raise TypeError("amount must be a number, not a bool")
    if isinstance(amount, int):
        return amount
    if isinstance(amount, float):
        return amount
    # str or Decimal -> validate via Decimal, then emit as a JSON number.
    dec = amount if isinstance(amount, Decimal) else Decimal(str(amount).strip())
    if dec == dec.to_integral_value():
        return int(dec)
    return float(dec)


class QintClient:
    """A thin, typed client over the Qint merchant API.

    Args:
        api_key: A Qint API key (``qk_live_…``). Sent as ``Authorization: Bearer``.
        base_url: API base URL. Defaults to the production gateway.
        timeout: Per-request timeout in seconds.
        transport: Optional custom :class:`~qint.http.Transport` (used by tests).
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[Transport] = None,
    ) -> None:
        if not api_key or not str(api_key).strip():
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport: Transport = transport or UrllibTransport()

    # -- public API ---------------------------------------------------------

    def create_intent(
        self,
        amount: AmountLike,
        currency: CurrencyLike,
        *,
        idempotency_key: str,
        title: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> Intent:
        """Create a payment intent (needs an API key with the ``Write`` scope).

        ``idempotency_key`` is required and must be unique per merchant (your
        order id works well) — the API rejects creates without one. Retrying
        with the same key returns the original intent instead of a duplicate.

        Returns the created (or, on an idempotent replay, the existing) intent.
        Send the buyer to ``intent.checkout_url`` to complete payment.
        """
        if not idempotency_key or not str(idempotency_key).strip():
            raise ValueError("idempotency_key is required")
        body: Dict[str, Any] = {
            "amount": _amount_to_json(amount),
            "currency": str(currency),
            "idempotencyKey": idempotency_key,
        }
        if title is not None:
            body["title"] = title
        if return_url is not None:
            body["returnUrl"] = return_url

        resp = self._request("POST", "/intents", body=body)
        return Intent.from_dict(self._json(resp))

    def get_intent(self, intent_id: str) -> Intent:
        """Fetch a single intent by id (needs the ``Read`` scope)."""
        if not intent_id or not str(intent_id).strip():
            raise ValueError("intent_id is required")
        resp = self._request("GET", f"/intents/{quote(str(intent_id), safe='')}")
        return Intent.from_dict(self._json(resp))

    def list_intents(
        self,
        *,
        status: Optional[StatusLike] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> IntentList:
        """List intents, most-recent first (needs the ``Read`` scope)."""
        params: Dict[str, str] = {}
        if status is not None:
            params["status"] = str(status)
        if page is not None:
            params["page"] = str(page)
        if page_size is not None:
            params["pageSize"] = str(page_size)
        path = "/intents"
        if params:
            path = f"{path}?{urlencode(params)}"
        resp = self._request("GET", path)
        return IntentList.from_dict(self._json(resp))

    # -- internals ----------------------------------------------------------

    def _request(
        self, method: str, path: str, *, body: Optional[Dict[str, Any]] = None
    ) -> HttpResponse:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": f"qint-python/{__version__}",
        }
        data: Optional[bytes] = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        resp = self._transport.request(
            method, url, headers=headers, body=data, timeout=self.timeout
        )
        if not 200 <= resp.status < 300:
            raise self._to_api_error(resp)
        return resp

    @staticmethod
    def _json(resp: HttpResponse) -> Dict[str, Any]:
        if not resp.body:
            return {}
        # parse_float=Decimal keeps monetary amounts exact.
        return json.loads(resp.body.decode("utf-8"), parse_float=Decimal)

    @staticmethod
    def _to_api_error(resp: HttpResponse) -> QintApiError:
        text = resp.text()
        problem: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(text) if text else None
            if isinstance(parsed, dict):
                problem = parsed
        except ValueError:
            problem = None
        detail = title = type_ = None
        if problem is not None:
            detail = problem.get("detail")
            title = problem.get("title")
            type_ = problem.get("type")
        return QintApiError(
            resp.status,
            detail,
            title=title,
            type=type_,
            problem=problem,
            body=text or None,
        )
