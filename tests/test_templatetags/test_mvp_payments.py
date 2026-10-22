"""The template tag that renders each available contribution's card."""

from django.urls import reverse

from mvp_payments.namespaces.stripe import stripe_contribution
from mvp_payments.templatetags.mvp_payments import payment_cards


class TestPaymentCards:
    def test_renders_one_card_for_an_available_contribution(self, monkeypatch):
        monkeypatch.setattr(
            "mvp_payments.templatetags.mvp_payments.available_contributions",
            lambda: (stripe_contribution,),
        )

        html = payment_cards()

        expected_url = reverse("payments:stripe-subscription")
        assert html.count(f'href="{expected_url}"') == 1
        assert str(stripe_contribution.pages[0].label) in html

    def test_renders_nothing_when_no_contribution_is_available(self, monkeypatch):
        monkeypatch.setattr(
            "mvp_payments.templatetags.mvp_payments.available_contributions",
            lambda: (),
        )

        assert payment_cards() == ""
