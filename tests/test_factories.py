"""Every factory builds a saved, readable row of its backend model."""

import pytest

from tests.factories import (
    FeatureFactory,
    PriceFactory,
    ProductFactory,
    ProductFeatureFactory,
    StripeUserFactory,
    SubscriptionFactory,
    SubscriptionItemFactory,
)


@pytest.mark.django_db
class TestFactories:
    """One factory per backend model this page reads (Article X)."""

    def test_stripe_user_factory_builds_a_saved_row(self):
        stripe_user = StripeUserFactory()
        assert stripe_user.pk is not None
        assert stripe_user.customer_id

    def test_feature_factory_builds_a_saved_row(self):
        feature = FeatureFactory()
        assert feature.pk is not None

    def test_product_factory_builds_a_saved_row(self):
        product = ProductFactory()
        assert product.pk is not None
        assert product.name

    def test_product_feature_factory_builds_a_saved_row(self):
        product_feature = ProductFeatureFactory()
        assert product_feature.pk is not None
        assert product_feature.product_id
        assert product_feature.feature_id

    def test_price_factory_builds_a_saved_row(self):
        price = PriceFactory()
        assert price.pk is not None
        assert price.currency

    def test_subscription_factory_builds_a_saved_row(self):
        subscription = SubscriptionFactory()
        assert subscription.pk is not None
        assert subscription.stripe_user_id is not None

    def test_subscription_item_factory_builds_a_saved_row(self):
        item = SubscriptionItemFactory()
        assert item.pk is not None
        assert item.subscription_id is not None
        assert item.price_id is not None
