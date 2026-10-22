"""Reading the Stripe app's subscriptions as presentation objects."""

import inspect
from datetime import UTC, datetime

import pytest

from mvp_payments.namespaces import stripe_records
from mvp_payments.namespaces.stripe_records import (
    CurrentSubscription,
    SubscriptionReader,
)
from tests.factories import StripeCustomerFactory, StripeSubscriptionFactory


def subscription_billed(interval, interval_count=1):
    return CurrentSubscription(
        status="active",
        name="Plan",
        amount=None,
        interval=interval,
        interval_count=interval_count,
        period_start=None,
        period_end=None,
    )


@pytest.mark.django_db
class TestSubscriptionReader:
    @pytest.mark.parametrize(
        "status",
        ["active", "trialing", "past_due", "unpaid", "incomplete", "paused", "new_one"],
    )
    def test_returns_one_entry_per_current_subscription_shown_with_its_own_status(
        self, user, status
    ):
        StripeSubscriptionFactory(customer__user=user, status=status)

        subscriptions = SubscriptionReader.for_user(user)

        assert len(subscriptions) == 1
        assert isinstance(subscriptions[0], CurrentSubscription)
        assert subscriptions[0].status == status

    @pytest.mark.parametrize("status", ["canceled", "incomplete_expired"])
    def test_a_subscription_that_has_ended_is_absent(self, user, status):
        StripeSubscriptionFactory(customer__user=user, status=status)

        assert SubscriptionReader.for_user(user) == ()

    def test_another_persons_subscription_is_absent(self, user):
        StripeCustomerFactory(user=user)
        StripeSubscriptionFactory(status="active")

        assert SubscriptionReader.for_user(user) == ()

    def test_a_person_with_no_customer_record_gets_an_empty_result_and_nothing_raises(
        self, user
    ):
        assert SubscriptionReader.for_user(user) == ()

    def test_every_subscription_a_person_holds_is_listed_newest_period_first(
        self, user
    ):
        customer = StripeCustomerFactory(user=user)
        older = StripeSubscriptionFactory(
            customer=customer,
            product_name="Older",
            current_period_end=datetime(2026, 1, 1, tzinfo=UTC),
        )
        newer = StripeSubscriptionFactory(
            customer=customer,
            product_name="Newer",
            current_period_end=datetime(2026, 6, 1, tzinfo=UTC),
        )

        names = [
            subscription.name for subscription in SubscriptionReader.for_user(user)
        ]

        assert names == [newer.product_name, older.product_name]

    def test_each_entry_carries_its_own_name_amount_interval_and_period(self, user):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 2, 1, tzinfo=UTC)
        StripeSubscriptionFactory(
            customer__user=user,
            product_name="Premium",
            amount=2500,
            currency="usd",
            interval="week",
            interval_count=2,
            current_period_start=start,
            current_period_end=end,
        )

        (current,) = SubscriptionReader.for_user(user)

        assert current.name == "Premium"
        assert current.amount.minor_units == 2500
        assert current.amount.currency == "USD"
        assert current.interval == "week"
        assert current.interval_count == 2
        assert current.period_start == start
        assert current.period_end == end

    def test_a_price_with_no_fixed_amount_carries_no_amount(self, user):
        StripeSubscriptionFactory(customer__user=user, amount=None)

        (current,) = SubscriptionReader.for_user(user)

        assert current.amount is None

    def test_a_zero_decimal_price_recorded_in_lower_case_still_converts(self, user):
        StripeSubscriptionFactory(customer__user=user, amount=2000, currency="jpy")

        (current,) = SubscriptionReader.for_user(user)

        assert str(current.amount) == "2,000 JPY"


class TestFrequencyDisplay:
    def test_a_count_of_one_renders_the_singular_form(self):
        assert subscription_billed("month").frequency_display == "every month"

    def test_a_count_above_one_renders_the_plural_form(self):
        assert subscription_billed("week", 2).frequency_display == "every 2 weeks"

    def test_an_unrecognised_interval_renders_as_itself(self):
        assert subscription_billed("quarter").frequency_display == "quarter_1"

    def test_no_interval_renders_nothing(self):
        assert subscription_billed("").frequency_display == ""


class TestFrequencyWords:
    def test_a_count_of_one_is_the_singular_form(self):
        assert CurrentSubscription.frequency_words("year", 1) == "every year"

    def test_a_count_above_one_is_the_plural_form(self):
        assert CurrentSubscription.frequency_words("month", 3) == "every 3 months"

    def test_an_unrecognised_interval_is_itself_with_its_count(self):
        assert CurrentSubscription.frequency_words("quarter", 2) == "quarter_2"

    def test_no_interval_is_nothing(self):
        assert CurrentSubscription.frequency_words("", 1) == ""

    def test_a_subscription_says_the_same_as_the_helper(self):
        assert subscription_billed("week", 2).frequency_display == (
            CurrentSubscription.frequency_words("week", 2)
        )


class TestNoStatusIsNamed:
    def test_no_status_is_named_in_the_source(self):
        source = inspect.getsource(stripe_records)
        for status in (
            "active",
            "trialing",
            "past_due",
            "canceled",
            "incomplete",
            "incomplete_expired",
            "unpaid",
            "ended",
        ):
            assert status not in source
