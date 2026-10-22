"""What the plans components read, for the person making the request."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from mvp_payments.namespaces.stripe_plans import PlanChoices
from mvp_payments.stripe.catalogue import Catalogue
from tests.factories import StripeSubscriptionFactory
from tests.stripe_fake import price_payload, product_payload


def request_for(user, path="/plans/", **query):
    request = RequestFactory().get(path, query)
    request.user = user
    return request


def product(stripe_id, name):
    return {**product_payload(stripe_id, name), "active": True}


@pytest.fixture
def catalogue(stripe_fake):
    basic = product("prod_basic", "Basic")
    pro = product("prod_pro", "Pro")
    stripe_fake.respond_with_list(
        "/v1/prices",
        [
            price_payload(
                "price_basic_year", basic, unit_amount=20000, interval="year"
            ),
            price_payload("price_basic_month", basic, unit_amount=2000),
            price_payload("price_pro_month", pro, unit_amount=5000),
            price_payload(
                "price_pro_quarter", pro, unit_amount=13000, interval_count=3
            ),
        ],
    )
    return stripe_fake


class TestPlanChoices:
    def test_the_prices_are_the_catalogues_prices(self, catalogue):
        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert [p["id"] for p in plans["prices"]] == [
            "price_basic_month",
            "price_basic_year",
            "price_pro_month",
            "price_pro_quarter",
        ]

    def test_intervals_are_listed_once_each_shortest_first(self, catalogue):
        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert [i["key"] for i in plans["intervals"]] == [
            "month_1",
            "month_3",
            "year_1",
        ]

    def test_the_switch_is_ordered_by_the_catalogues_own_billing_lengths(
        self, catalogue, monkeypatch
    ):
        monkeypatch.setitem(Catalogue.BILLING_DAYS, "year", 1)

        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert [i["key"] for i in plans["intervals"]] == [
            "year_1",
            "month_1",
            "month_3",
        ]

    def test_every_interval_has_a_label_for_the_switch(self, catalogue):
        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert all(i["label"] for i in plans["intervals"])

    def test_the_switch_starts_on_the_shortest_interval(self, catalogue):
        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert plans["first_interval"] == "month_1"
        assert plans["ready"] == ""

    def test_the_switch_starts_on_the_interval_of_the_plan_picked_before_signing_in(
        self, catalogue
    ):
        request = request_for(AnonymousUser(), plan="price_basic_year")

        plans = PlanChoices.for_request(request)

        assert plans["first_interval"] == "year_1"
        assert plans["ready"] == "price_basic_year"

    def test_a_plan_no_longer_on_offer_leaves_the_switch_on_the_shortest(
        self, catalogue
    ):
        request = request_for(AnonymousUser(), plan="price_gone")

        plans = PlanChoices.for_request(request)

        assert plans["first_interval"] == "month_1"

    def test_an_anonymous_visitor_holds_nothing_and_is_not_signed_in(self, catalogue):
        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert plans["held"] == []
        assert plans["signed_in"] is False

    @pytest.mark.django_db
    def test_a_signed_in_person_holds_the_prices_they_currently_subscribe_to(
        self, catalogue, user
    ):
        StripeSubscriptionFactory(
            customer__user=user, price_id="price_pro_month", status="active"
        )
        StripeSubscriptionFactory(
            customer=user.stripe_customer,
            price_id="price_basic_year",
            status="canceled",
        )

        plans = PlanChoices.for_request(request_for(user))

        assert plans["held"] == ["price_pro_month"]
        assert plans["signed_in"] is True

    def test_the_page_the_plans_are_on_is_where_sign_in_and_cancelling_return_to(
        self, catalogue
    ):
        plans = PlanChoices.for_request(request_for(AnonymousUser(), "/offers/"))

        assert plans["return_to"] == "/offers/"

    def test_the_ways_onward_are_addresses_that_exist(self, catalogue, settings):
        settings.LOGIN_URL = "/sign-in/"

        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert plans["login_url"] == "/sign-in/"
        assert plans["subscriptions_url"] == "/account/billing/subscription/"
        assert plans["checkout_url"].startswith("/account/billing/")

    def test_an_unavailable_catalogue_has_no_prices_and_no_intervals(self, stripe_fake):
        stripe_fake.become_unreachable("GET", "/v1/prices")

        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert plans["prices"] is None
        assert plans["intervals"] == []
        assert plans["first_interval"] == ""

    def test_an_empty_catalogue_has_an_empty_list_of_prices(self, stripe_fake):
        stripe_fake.respond_with_list("/v1/prices", [])

        plans = PlanChoices.for_request(request_for(AnonymousUser()))

        assert plans["prices"] == []
        assert plans["intervals"] == []


class TestIntervalLabel:
    @pytest.mark.parametrize(
        ("interval", "count"), [("month", 1), ("year", 1), ("month", 3), ("week", 2)]
    )
    def test_a_known_interval_has_a_label_and_a_key(self, interval, count):
        price = price_payload(
            "price_x", product("prod_x", "X"), interval=interval, interval_count=count
        )

        assert PlanChoices.interval_label(price)
        assert PlanChoices.interval_key(price) == f"{interval}_{count}"

    def test_an_unknown_interval_is_labelled_as_itself_not_dropped(self):
        price = price_payload("price_x", product("prod_x", "X"), interval="quarter")

        assert PlanChoices.interval_label(price) == "quarter"
