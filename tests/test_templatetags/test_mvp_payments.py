"""The template tag that renders each available contribution's card."""

import re

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from mvp_payments.namespaces.stripe import stripe_contribution
from mvp_payments.templatetags.mvp_payments import (
    payment_cards,
    price_frequency,
    price_interval,
    price_money,
)
from tests.stripe_fake import price_payload, product_payload


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


@pytest.fixture
def on_offer(stripe_fake):
    pro = {
        **product_payload("prod_pro", "Pro"),
        "active": True,
        "marketing_features": [{"name": "Priority support"}],
    }
    stripe_fake.respond_with_list(
        "/v1/prices",
        [
            price_payload("price_pro_month", pro, unit_amount=5000),
            price_payload("price_pro_year", pro, unit_amount=50000, interval="year"),
        ],
    )
    return stripe_fake


def request_on(path, user=None, **query):
    request = RequestFactory().get(path, query)
    request.user = user or AnonymousUser()
    return request


PLACED = (
    "{% load mvp_payments %}{% stripe_plans as plans %}"
    '<section id="landing">{% if plans.prices %}<c-stripe.plans :plans="plans" />'
    "{% endif %}</section>"
)


@pytest.mark.django_db
class TestStripePlansPlacement:
    def test_a_project_template_shows_the_plans_without_a_view_of_its_own(
        self, cotton_render_string, on_offer
    ):
        html = cotton_render_string(PLACED, {"request": request_on("/pricing/")})

        assert 'id="price_pro_month"' in html
        assert 'id="price_pro_year"' in html
        assert "50.00 USD" in html
        assert "Priority support" in html

    def test_a_visitor_who_signs_in_from_there_comes_back_to_that_page_with_the_plan(
        self, cotton_render_string, on_offer
    ):
        html = cotton_render_string(PLACED, {"request": request_on("/pricing/")})

        assert "next=%2Fpricing%2F%3Fplan%3Dprice_pro_year%23price_pro_year" in html

    def test_a_signed_in_person_starts_checkout_from_there_as_from_the_plans_page(
        self, cotton_render_string, on_offer, user
    ):
        html = cotton_render_string(
            PLACED, {"request": request_on("/pricing/", user=user)}
        )

        assert f'action="{reverse("payments:stripe-checkout")}"' in html
        assert 'name="price" value="price_pro_year"' in html
        assert 'name="return_to" value="/pricing/"' in html

    def test_a_project_loop_replaces_one_part_on_that_page_only(
        self, cotton_render_string, on_offer
    ):
        loop = (
            "{% load mvp_payments %}{% stripe_plans as plans %}"
            "{% for price in plans.prices %}<article>"
            '<c-stripe.plan-price :price="price" />'
            '<c-stripe.plan-choose :price="price" :plans="plans" />'
            "</article>{% endfor %}"
        )
        context = {"request": request_on("/pricing/")}

        replaced = cotton_render_string(loop, context)
        elsewhere = cotton_render_string(PLACED, context)

        assert replaced.count("<article>") == 2
        assert "50.00 USD" in replaced
        assert "next=%2Fpricing%2F" in replaced
        assert "Priority support" not in replaced
        assert "Priority support" in elsewhere

    def test_a_project_loop_carries_the_note_the_choose_control_is_described_by(
        self, cotton_render_string, on_offer
    ):
        loop = (
            "{% load mvp_payments %}{% stripe_plans as plans %}"
            "{% for price in plans.prices %}<article>"
            '<c-stripe.plan-choose :price="price" :plans="plans" />'
            "</article>{% endfor %}"
            '<p id="mvp-payments-checkout-note">Payment is taken on Stripe.</p>'
        )

        html = cotton_render_string(loop, {"request": request_on("/pricing/")})

        described_by = set(re.findall(r'aria-describedby="([^"]+)"', html))
        assert described_by
        for element_id in described_by:
            assert f'id="{element_id}"' in html
