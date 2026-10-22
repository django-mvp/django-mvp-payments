"""The template tag that renders each available contribution's card."""

from django.urls import reverse

from mvp_payments.namespaces.stripe import stripe_contribution
from mvp_payments.templatetags.mvp_payments import (
    payment_cards,
    price_frequency,
    price_interval,
    price_money,
)
from tests.stripe_fake import price_payload


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


def a_price(**kwargs):
    return price_payload("price_x", {"id": "prod_x", "name": "X"}, **kwargs)


class TestPriceMoney:
    def test_a_two_decimal_amount_keeps_its_cents(self):
        assert (
            str(price_money(a_price(unit_amount=2000, currency="usd"))) == "20.00 USD"
        )

    def test_a_zero_decimal_amount_is_not_divided(self):
        assert str(price_money(a_price(unit_amount=500000, currency="jpy"))) == (
            "500,000 JPY"
        )

    def test_a_three_decimal_amount_keeps_its_thousandths(self):
        assert str(price_money(a_price(unit_amount=12500, currency="kwd"))) == (
            "12.500 KWD"
        )

    def test_a_price_without_an_amount_has_no_money(self):
        assert price_money(a_price(unit_amount=None)) is None

    def test_nothing_has_no_money(self):
        assert price_money(None) is None


class TestPriceFrequency:
    def test_a_monthly_price_bills_every_month(self):
        assert price_frequency(a_price()) == "every month"

    def test_a_three_monthly_price_says_how_many(self):
        assert price_frequency(a_price(interval_count=3)) == "every 3 months"

    def test_an_unknown_interval_is_shown_as_itself(self):
        assert price_frequency(a_price(interval="quarter")) == "quarter_1"

    def test_nothing_has_no_frequency(self):
        assert price_frequency(None) == ""


class TestPriceInterval:
    def test_the_key_joins_the_unit_and_the_count(self):
        assert price_interval(a_price(interval="week", interval_count=2)) == "week_2"
