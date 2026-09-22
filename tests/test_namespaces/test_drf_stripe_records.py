"""Reading the backend's records as presentation objects (D1)."""

import inspect

import pytest

from mvp_payments.money import Money
from mvp_payments.namespaces import drf_stripe_records
from mvp_payments.namespaces.drf_stripe_records import (
    CurrentSubscription,
    Plan,
    SubscriptionReader,
)
from tests.factories import (
    FeatureFactory,
    PriceFactory,
    ProductFactory,
    ProductFeatureFactory,
    StripeUserFactory,
    SubscriptionFactory,
    SubscriptionItemFactory,
)


def _plan(frequency):
    return Plan(name="Plan", amount=Money(0), frequency=frequency, quantity=1)


@pytest.mark.django_db
class TestSubscriptionReader:
    """``for_user`` reads only what the backend itself calls current."""

    def test_returns_one_entry_per_subscription_the_backend_calls_current(self, user):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
        SubscriptionItemFactory(subscription=subscription)

        subscriptions = SubscriptionReader.for_user(user)

        assert len(subscriptions) == 1
        assert isinstance(subscriptions[0], CurrentSubscription)
        assert subscriptions[0].status == "active"

    def test_a_subscription_the_backend_does_not_call_current_is_absent(self, user):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="canceled")
        SubscriptionItemFactory(subscription=subscription)

        assert SubscriptionReader.for_user(user) == ()

    def test_another_persons_subscription_is_absent(self, user):
        StripeUserFactory(user=user)
        other_stripe_user = StripeUserFactory()
        other_subscription = SubscriptionFactory(
            stripe_user=other_stripe_user, status="active"
        )
        SubscriptionItemFactory(subscription=other_subscription)

        assert SubscriptionReader.for_user(user) == ()

    def test_a_person_with_no_customer_record_gets_an_empty_result_and_nothing_raises(
        self, user
    ):
        assert SubscriptionReader.for_user(user) == ()

    def test_each_item_carries_its_own_plan_name_amount_and_frequency(self, user):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
        price = PriceFactory(
            nickname=None,
            price=2500,
            currency="USD",
            freq="month_1",
            product__name="Premium",
        )
        SubscriptionItemFactory(subscription=subscription, price=price, quantity=2)

        (current,) = SubscriptionReader.for_user(user)

        assert len(current.plans) == 1
        plan = current.plans[0]
        assert plan.name == "Premium"
        assert plan.amount.minor_units == 2500
        assert plan.amount.currency == "USD"
        assert plan.frequency == "month_1"
        assert plan.quantity == 2

    def test_the_plans_name_is_the_price_nickname_where_set(self, user):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
        price = PriceFactory(nickname="Premium monthly", product__name="Premium")
        SubscriptionItemFactory(subscription=subscription, price=price)

        (current,) = SubscriptionReader.for_user(user)

        assert current.plans[0].name == "Premium monthly"


@pytest.mark.django_db
class TestPlanFeatures:
    """A plan carries the features recorded against its own product (FR-009), never a
    different product's and never the person's (Decisions.md "Why features come from
    the plan rather than from the person")."""

    def _subscribe(self, user, product):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
        price = PriceFactory(product=product)
        SubscriptionItemFactory(subscription=subscription, price=price)
        (current,) = SubscriptionReader.for_user(user)
        return current.plans[0]

    def test_features_recorded_against_the_product_are_carried(self, user):
        product = ProductFactory()
        ProductFeatureFactory(product=product, feature=FeatureFactory(feature_id="a"))
        ProductFeatureFactory(product=product, feature=FeatureFactory(feature_id="b"))

        plan = self._subscribe(user, product)

        assert {feature.identifier for feature in plan.features} == {"a", "b"}

    def test_a_features_own_description_is_carried(self, user):
        product = ProductFactory()
        ProductFeatureFactory(
            product=product,
            feature=FeatureFactory(
                feature_id="priority_support", description="Priority support"
            ),
        )

        plan = self._subscribe(user, product)

        (feature,) = plan.features
        assert feature.description == "Priority support"

    def test_a_feature_with_no_description_carries_its_identifier_in_its_place(
        self, user
    ):
        product = ProductFactory()
        ProductFeatureFactory(
            product=product,
            feature=FeatureFactory(feature_id="priority_support", description=""),
        )

        plan = self._subscribe(user, product)

        (feature,) = plan.features
        assert feature.description == "priority_support"

    def test_a_product_with_no_features_carries_an_empty_collection(self, user):
        product = ProductFactory()

        plan = self._subscribe(user, product)

        assert plan.features == ()

    def test_a_feature_recorded_against_a_different_product_never_appears(self, user):
        product = ProductFactory()
        other_product = ProductFactory()
        ProductFeatureFactory(
            product=other_product, feature=FeatureFactory(feature_id="other_only")
        )

        plan = self._subscribe(user, product)

        assert plan.features == ()


class TestPlanFrequencyDisplay:
    """``frequency_display`` renders the backend's ``interval_count`` encoding through ngettext,
    and shows an unrecognised one as itself (Article XVI).
    """

    def test_a_count_of_one_renders_the_singular_form(self):
        assert _plan("month_1").frequency_display == "every month"

    def test_a_count_above_one_renders_the_plural_form(self):
        assert _plan("week_2").frequency_display == "every 2 weeks"

    def test_an_unrecognised_interval_renders_as_itself(self):
        assert _plan("quarter_1").frequency_display == "quarter_1"

    def test_no_frequency_renders_nothing(self):
        assert _plan(None).frequency_display == ""


class TestNoStatusIsNamed:
    """No status string appears anywhere in this module (D1)."""

    def test_no_access_granting_status_is_named_in_the_source(self):
        source = inspect.getsource(drf_stripe_records)
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
