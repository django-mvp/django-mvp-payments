"""The plans on offer, read from Stripe and kept in the project's cache."""

import logging
import time

import pytest
from django.apps import apps
from django.core.cache import cache

from mvp_payments.stripe.catalogue import Catalogue
from tests.stripe_fake import price_payload, product_payload

PRICES = "/v1/prices"


def product(stripe_id: str, name: str, **extra) -> dict:
    return {**product_payload(stripe_id, name), "active": True, **extra}


@pytest.fixture
def later(monkeypatch):
    """Move the clock forward, for the cache's expiry."""
    now = time.time()
    offset = {"seconds": 0}
    monkeypatch.setattr(time, "time", lambda: now + offset["seconds"])

    def move(seconds: int) -> None:
        offset["seconds"] += seconds

    return move


@pytest.fixture
def two_pages(stripe_fake):
    basic = product("prod_basic", "Basic")
    pro = product("prod_pro", "Pro")
    stripe_fake.respond_with_pages(
        PRICES,
        [
            [
                price_payload("price_pro_month", pro, unit_amount=5000),
                price_payload(
                    "price_basic_year", basic, unit_amount=20000, interval="year"
                ),
            ],
            [price_payload("price_basic_month", basic, unit_amount=2000)],
        ],
    )
    return stripe_fake


class TestCatalogue:
    def test_every_price_on_every_page_is_returned_ordered(self, two_pages):
        prices = Catalogue.prices()

        assert [p["id"] for p in prices] == [
            "price_basic_month",
            "price_basic_year",
            "price_pro_month",
        ]

    def test_prices_are_requested_active_recurring_with_the_product_expanded(
        self, two_pages
    ):
        Catalogue.prices()

        _, _, params = two_pages.requests[0]
        assert params["active"] == ["true"]
        assert params["type"] == ["recurring"]
        assert params["limit"] == ["100"]
        assert "data.product" in [
            value for values in params.values() for value in values
        ]

    def test_the_prices_are_plain_dictionaries_with_their_product(self, two_pages):
        price = Catalogue.prices()[0]

        assert type(price) is dict
        assert type(price["product"]) is dict
        assert price["product"]["name"] == "Basic"
        assert price["recurring"]["interval_count"] == 1

    def test_the_second_call_makes_no_request(self, two_pages):
        Catalogue.prices()
        asked = len(two_pages.requests)

        Catalogue.prices()

        assert len(two_pages.requests) == asked

    def test_clearing_forces_a_fetch(self, two_pages):
        Catalogue.prices()
        asked = len(two_pages.requests)

        Catalogue.clear()
        Catalogue.prices()

        assert len(two_pages.requests) > asked

    def test_an_empty_catalogue_is_cached_as_empty_not_as_unavailable(
        self, stripe_fake
    ):
        stripe_fake.respond_with_list(PRICES, [])

        assert Catalogue.prices() == []
        assert Catalogue.prices() == []
        assert len(stripe_fake.requests) == 1

    @pytest.mark.parametrize(
        "unwanted",
        [
            price_payload(
                "price_x", product("prod_x", "X", active=False), unit_amount=100
            ),
            price_payload(
                "price_x", {"id": "prod_x", "object": "product", "deleted": True}
            ),
            price_payload("price_x", product("prod_x", "X"), unit_amount=None),
            price_payload("price_x", product("prod_x", "X"), billing_scheme="tiered"),
            price_payload("price_x", product("prod_x", "X"), usage_type="metered"),
            {**price_payload("price_x", product("prod_x", "X")), "type": "one_time"},
        ],
        ids=[
            "inactive_product",
            "deleted_product",
            "null_amount",
            "tiered",
            "metered",
            "one_off",
        ],
    )
    def test_a_price_without_a_single_recurring_amount_is_left_out(
        self, stripe_fake, unwanted
    ):
        wanted = price_payload("price_ok", product("prod_ok", "OK"))
        stripe_fake.respond_with_list(PRICES, [unwanted, wanted])

        assert [p["id"] for p in Catalogue.prices()] == ["price_ok"]

    def test_products_are_ordered_by_their_cheapest_price(self, stripe_fake):
        dear = product("prod_dear", "Dear")
        cheap = product("prod_cheap", "Cheap")
        stripe_fake.respond_with_list(
            PRICES,
            [
                price_payload("price_dear_month", dear, unit_amount=9000),
                price_payload(
                    "price_cheap_year", cheap, unit_amount=7000, interval="year"
                ),
                price_payload("price_cheap_month", cheap, unit_amount=1000),
            ],
        )

        assert [p["id"] for p in Catalogue.prices()] == [
            "price_cheap_month",
            "price_cheap_year",
            "price_dear_month",
        ]

    def test_a_missing_secret_key_returns_none_without_a_request_or_a_cache_entry(
        self, stripe_fake, settings
    ):
        settings.MVP_PAYMENTS = {}

        assert Catalogue.prices() is None
        assert stripe_fake.requests == []
        assert cache.get(Catalogue.KEY, "empty") == "empty"

    def test_a_stripe_error_returns_none(self, stripe_fake):
        stripe_fake.become_unreachable("GET", PRICES)

        assert Catalogue.prices() is None

    def test_a_stripe_error_is_not_fetched_again_within_sixty_seconds(
        self, stripe_fake, later
    ):
        stripe_fake.become_unreachable("GET", PRICES)
        Catalogue.prices()

        later(59)
        Catalogue.prices()

        assert len(stripe_fake.requests) == 1

    def test_a_stripe_error_is_fetched_again_after_sixty_seconds(
        self, stripe_fake, later
    ):
        stripe_fake.become_unreachable("GET", PRICES)
        Catalogue.prices()
        stripe_fake.respond_with_list(
            PRICES, [price_payload("price_ok", product("prod_ok", "OK"))]
        )

        later(61)

        assert [p["id"] for p in Catalogue.prices()] == ["price_ok"]

    def test_clearing_ends_the_unavailable_period(self, stripe_fake):
        stripe_fake.become_unreachable("GET", PRICES)
        Catalogue.prices()
        stripe_fake.respond_with_list(
            PRICES, [price_payload("price_ok", product("prod_ok", "OK"))]
        )

        Catalogue.clear()

        assert [p["id"] for p in Catalogue.prices()] == ["price_ok"]

    def test_a_stripe_error_logs_its_type_and_never_its_message(
        self, stripe_fake, caplog
    ):
        stripe_fake.respond_with_message_echoing(
            "GET", PRICES, "sk_test_not_a_real_key"
        )

        with caplog.at_level(logging.ERROR, logger="mvp_payments.stripe.catalogue"):
            Catalogue.prices()

        assert (
            "AuthenticationError" in caplog.text or "InvalidRequestError" in caplog.text
        )
        assert "sk_test_not_a_real_key" not in caplog.text

    def test_entries_are_kept_for_the_configured_timeout(
        self, two_pages, settings, later
    ):
        settings.MVP_PAYMENTS = {
            **settings.MVP_PAYMENTS,
            "STRIPE_CATALOGUE_TIMEOUT": 120,
        }
        Catalogue.prices()
        asked = len(two_pages.requests)

        later(119)
        Catalogue.prices()
        assert len(two_pages.requests) == asked

        later(2)
        Catalogue.prices()
        assert len(two_pages.requests) > asked

    def test_the_timeout_is_an_hour_unless_configured(self, settings):
        settings.MVP_PAYMENTS = {}

        assert Catalogue.timeout() == 3600

    def test_a_price_is_found_by_its_id(self, two_pages):
        assert Catalogue.price("price_pro_month")["product"]["name"] == "Pro"

    def test_a_price_not_on_offer_is_none(self, two_pages):
        assert Catalogue.price("price_gone") is None

    def test_a_price_is_none_when_the_catalogue_is_unavailable(self, stripe_fake):
        stripe_fake.become_unreachable("GET", PRICES)

        assert Catalogue.price("price_pro_month") is None


class TestStripeConfigCatalogue:
    def test_the_app_config_hands_out_the_catalogue(self):
        config = apps.get_app_config("mvp_payments_stripe")

        assert config.catalogue is Catalogue
