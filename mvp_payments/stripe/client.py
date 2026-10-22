"""The one place a Stripe client is built."""

from __future__ import annotations

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#: The Stripe API version the app is written against. Every call carries it, so a change
#: to the account's default version cannot change what the app receives.
API_VERSION = "2026-09-30.endive"

#: Replaced only by the test suite, to keep requests off the network.
_http_client: stripe.HTTPClient | None = None


def client() -> stripe.StripeClient:
    """Build a Stripe client from the project's settings.

    The SDK's module-level configuration is never read or written, so another
    integration in the same process cannot change which key or version this uses.

    Returns:
        A client for ``API_VERSION``, authorised with ``STRIPE_SECRET_KEY``.

    Raises:
        ImproperlyConfigured: If ``MVP_PAYMENTS["STRIPE_SECRET_KEY"]`` is missing or empty.
    """
    secret_key = getattr(settings, "MVP_PAYMENTS", {}).get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise ImproperlyConfigured(
            "MVP_PAYMENTS['STRIPE_SECRET_KEY'] must be set to use mvp_payments.stripe."
        )
    return stripe.StripeClient(
        secret_key, stripe_version=API_VERSION, http_client=_http_client
    )
