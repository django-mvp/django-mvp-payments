"""The template tag that renders each available contribution's card."""

from django.urls import reverse
from mvp_payments.templatetags.mvp_payments import payment_cards

from mvp_payments.namespaces.drf_stripe import drf_stripe


class TestPaymentCards:
    """One card per available, reachable contribution — nothing otherwise (FR-006, FR-009)."""

    def test_renders_one_card_for_an_available_contribution(self, monkeypatch):
        monkeypatch.setattr(
            "mvp_payments.templatetags.mvp_payments.available_contributions",
            lambda: (drf_stripe,),
        )

        html = payment_cards()

        expected_url = reverse("payments:drf-stripe-subscription")
        assert html.count(f'href="{expected_url}"') == 1
        assert "Subscription" in html

    def test_renders_nothing_when_no_contribution_is_available(self, monkeypatch):
        monkeypatch.setattr(
            "mvp_payments.templatetags.mvp_payments.available_contributions",
            lambda: (),
        )

        assert payment_cards() == ""
