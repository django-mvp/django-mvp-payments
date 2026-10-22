"""The webhook address, which exists only while the Stripe app is installed."""

from django.urls import resolve, reverse

from mvp_payments.stripe.views import webhook
from tests.probes import run_probe

WEBHOOK_ADDRESS_PROBE = """
import json

import django

django.setup()

from django.urls import NoReverseMatch, Resolver404, resolve, reverse

try:
    reverse("payments:stripe-webhook")
    reverses = True
except NoReverseMatch:
    reverses = False

try:
    resolve("/account/billing/stripe/webhook/")
    resolves = True
except Resolver404:
    resolves = False

print(json.dumps({"reverses": reverses, "resolves": resolves}))
"""


class TestWebhookAddress:
    def test_the_address_is_mounted_with_the_packages_urls(self):
        url = reverse("payments:stripe-webhook")

        assert url == "/account/billing/stripe/webhook/"
        assert resolve(url).func is webhook

    def test_without_the_app_installed_the_address_does_not_resolve(self):
        result = run_probe(WEBHOOK_ADDRESS_PROBE, "tests.settings_without_stripe_app")

        assert result == {"reverses": False, "resolves": False}
