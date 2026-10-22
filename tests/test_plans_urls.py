"""The plans page's own URL configuration, which a project includes where it likes."""

from tests.probes import run_probe

_PLANS_ROUTE_PROBE = """
import json

import django

django.setup()

from django.urls import NoReverseMatch, reverse

try:
    reverse("payments_plans:stripe-plans")
    routed = True
except NoReverseMatch:
    routed = False

print(json.dumps({"routed": routed}))
"""


class TestPlansURLs:
    def test_the_plans_page_is_routed_when_the_stripe_app_is_installed(self):
        result = run_probe(_PLANS_ROUTE_PROBE, "tests.settings")

        assert result == {"routed": True}

    def test_nothing_is_routed_without_the_stripe_app(self):
        result = run_probe(_PLANS_ROUTE_PROBE, "tests.settings_without_stripe_app")

        assert result == {"routed": False}
