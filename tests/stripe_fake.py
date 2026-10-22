"""A Stripe that answers from canned JSON, for tests that must never reach the network.

``FakeStripe`` is a ``stripe.HTTPClient``, so the SDK's own request building, error mapping and
response parsing all run. Only the bytes on the wire are replaced. The app's own code is never
mocked: the ``stripe_fake`` fixture in ``conftest.py`` installs this client where
``mvp_payments.stripe.client.client()`` builds its ``StripeClient``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, urlsplit

import stripe

#: The signing secret the suite's settings carry.
WEBHOOK_SECRET = "whsec_not_a_real_secret"


class FakeStripe(stripe.HTTPClient):
    """Answers each ``(method, path)`` with a canned response and records every request.

    Attributes:
        requests: Every request received, as ``(method, path, params)``, where ``params``
            holds the query string for a GET and the form body for anything else.
    """

    name = "fake"

    def __init__(self) -> None:
        super().__init__()
        self._routes: dict[tuple[str, str], object] = {}
        self.requests: list[tuple[str, str, dict[str, list[str]]]] = []

    def respond(self, method: str, path: str, body: dict, status: int = 200) -> None:
        """Answer ``method`` on ``path`` with ``body``.

        Args:
            method: The HTTP method, such as ``"GET"``.
            path: The path without host or query string, such as ``"/v1/customers/cus_1"``.
            body: The JSON object to return.
            status: The HTTP status to return it with.
        """
        self._routes[(method, path)] = (json.dumps(body), status)

    def respond_with_list(self, path: str, objects: list[dict]) -> None:
        """Answer a GET on ``path`` with one complete page of ``objects``.

        Args:
            path: The list endpoint's path, such as ``"/v1/subscriptions"``.
            objects: The Stripe objects the list holds.
        """
        self.respond(
            "GET",
            path,
            {"object": "list", "data": objects, "has_more": False, "url": path},
        )

    def respond_with_error(
        self, method: str, path: str, code: str, status: int = 404
    ) -> None:
        """Answer ``method`` on ``path`` with a Stripe error body.

        Args:
            method: The HTTP method.
            path: The path without host or query string.
            code: Stripe's error code, such as ``"resource_missing"``.
            status: The HTTP status to return it with.
        """
        self.respond(
            method,
            path,
            {
                "error": {
                    "type": "invalid_request_error",
                    "code": code,
                    "message": f"canned {code}",
                }
            },
            status,
        )

    def respond_with_message_echoing(self, method: str, path: str, echoed: str) -> None:
        """Answer ``method`` on ``path`` with an authentication error that quotes ``echoed``.

        Stripe's real message for a bad key repeats part of it, which is how a secret ends up
        in a log if the whole message is logged.

        Args:
            method: The HTTP method.
            path: The path without host or query string.
            echoed: The text the message quotes.
        """
        self.respond(
            method,
            path,
            {
                "error": {
                    "type": "invalid_request_error",
                    "message": f"Invalid API Key provided: {echoed}",
                }
            },
            401,
        )

    def become_unreachable(self, method: str, path: str) -> None:
        """Make ``method`` on ``path`` fail as if Stripe could not be reached.

        Args:
            method: The HTTP method.
            path: The path without host or query string.
        """
        self._routes[(method, path)] = stripe.APIConnectionError("canned outage")

    def paths(self, method: str | None = None) -> list[str]:
        """List the paths requested, in order.

        Args:
            method: Only requests with this method, or all when ``None``.

        Returns:
            The request paths.
        """
        return [path for m, path, _ in self.requests if method in (None, m)]

    def request(self, method, url, headers, post_data=None, *, _usage=None):
        """Return the canned response for the request, recording it first.

        Args:
            method: The HTTP method.
            url: The full URL the SDK built.
            headers: The request headers.
            post_data: The form body of a non-GET request.
            _usage: Unused. The SDK's telemetry hint.

        Returns:
            The body, status and headers, as the SDK expects them.

        Raises:
            AssertionError: When no response was canned for the request.
            stripe.APIConnectionError: When the route was made unreachable.
        """
        method = method.upper()
        parts = urlsplit(url)
        params = parse_qs(parts.query if method == "GET" else post_data or "")
        self.requests.append((method, parts.path, params))
        canned = self._routes.get((method, parts.path))
        if canned is None:
            raise AssertionError(f"no canned Stripe response for {method} {parts.path}")
        if isinstance(canned, Exception):
            raise canned
        body, status = canned
        return body, status, {}


def sign_webhook(
    payload: str, secret: str = WEBHOOK_SECRET, timestamp: int | None = None
) -> str:
    """Sign a webhook payload exactly as Stripe documents.

    Args:
        payload: The raw request body.
        secret: The signing secret.
        timestamp: When it was signed, in epoch seconds. Defaults to now.

    Returns:
        The value for the ``Stripe-Signature`` header.
    """
    signed_at = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(
        secret.encode(), f"{signed_at}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return f"t={signed_at},v1={digest}"


def customer_payload(stripe_id: str, **extra) -> dict:
    """Build a Stripe customer object.

    Args:
        stripe_id: The customer's identifier.
        **extra: Fields to add or override.

    Returns:
        The object as Stripe returns it.
    """
    return {"id": stripe_id, "object": "customer", "email": None, **extra}


def product_payload(stripe_id: str, name: str) -> dict:
    """Build a Stripe product object.

    Args:
        stripe_id: The product's identifier.
        name: The product's name.

    Returns:
        The object as Stripe returns it.
    """
    return {"id": stripe_id, "object": "product", "name": name}


def subscription_payload(
    stripe_id: str,
    customer: str,
    *,
    status: str = "active",
    price_id: str = "price_1",
    product: str = "prod_1",
    amount: int | None = 2000,
    currency: str = "usd",
    interval: str = "month",
    interval_count: int = 1,
    period_start: int = 1_790_000_000,
    period_end: int = 1_792_592_000,
    cancel_at_period_end: bool = False,
    ended_at: int | None = None,
) -> dict:
    """Build a Stripe subscription object in the API version the app is written against.

    The billing period sits on the first item, not on the subscription.

    Args:
        stripe_id: The subscription's identifier.
        customer: The owning customer's identifier.
        status: The status Stripe reports.
        price_id: The price's identifier.
        product: The price's product identifier, unexpanded.
        amount: The price's unit amount in the minor unit, or ``None``.
        currency: The lower-case currency code.
        interval: The billing interval unit.
        interval_count: How many intervals between bills.
        period_start: The period's start, in epoch seconds.
        period_end: The period's end, in epoch seconds.
        cancel_at_period_end: Whether it ends when the period does.
        ended_at: When it ended, in epoch seconds, or ``None``.

    Returns:
        The object as Stripe returns it.
    """
    return {
        "id": stripe_id,
        "object": "subscription",
        "customer": customer,
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
        "ended_at": ended_at,
        "items": {
            "object": "list",
            "has_more": False,
            "url": f"/v1/subscription_items?subscription={stripe_id}",
            "data": [
                {
                    "id": f"si_{stripe_id}",
                    "object": "subscription_item",
                    "current_period_start": period_start,
                    "current_period_end": period_end,
                    "price": {
                        "id": price_id,
                        "object": "price",
                        "currency": currency,
                        "unit_amount": amount,
                        "product": product,
                        "recurring": {
                            "interval": interval,
                            "interval_count": interval_count,
                        },
                    },
                }
            ],
        },
    }


def checkout_session_payload(
    stripe_id: str,
    *,
    client_reference_id: str | None,
    customer: str | None,
    mode: str = "subscription",
) -> dict:
    """Build a Stripe Checkout Session object.

    Args:
        stripe_id: The session's identifier.
        client_reference_id: The reference the page passed through checkout.
        customer: The customer the purchase created or used.
        mode: The session's mode.

    Returns:
        The object as Stripe returns it.
    """
    return {
        "id": stripe_id,
        "object": "checkout.session",
        "mode": mode,
        "client_reference_id": client_reference_id,
        "customer": customer,
    }


def event_payload(event_type: str, data_object: dict, stripe_id: str = "evt_1") -> str:
    """Build a webhook body.

    Args:
        event_type: The event's type, such as ``"customer.subscription.updated"``.
        data_object: The object the event carries.
        stripe_id: The event's identifier.

    Returns:
        The JSON text Stripe would send.
    """
    return json.dumps(
        {
            "id": stripe_id,
            "object": "event",
            "type": event_type,
            "api_version": "2026-09-30.endive",
            "data": {"object": data_object},
        }
    )
