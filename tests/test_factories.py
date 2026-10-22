"""Every factory builds a saved, readable row of its model."""

import pytest

from tests.factories import StripeCustomerFactory, StripeSubscriptionFactory


@pytest.mark.django_db
class TestStripeAppFactories:
    def test_customer_factory_builds_a_saved_row_for_a_user(self):
        customer = StripeCustomerFactory()
        assert customer.pk is not None
        assert customer.user_id is not None

    def test_subscription_factory_builds_a_saved_row_on_a_customer(self):
        subscription = StripeSubscriptionFactory()
        assert subscription.pk is not None
        assert subscription.customer_id is not None
