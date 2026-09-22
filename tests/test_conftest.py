"""Fixtures wrapping the factories (Article X) — thin wrappers, nothing built inline."""

import pytest
from django.apps import apps


@pytest.mark.django_db
class TestSubscriberClientFixture:
    """``subscriber_client`` is a signed-in client whose person holds one active
    subscription covering one priced item of a product.
    """

    def test_is_signed_in_as_the_person_who_holds_the_subscription(
        self, subscriber_client, user
    ):
        assert subscriber_client.session["_auth_user_id"] == str(user.pk)

    def test_the_persons_stripe_user_holds_one_active_current_item(
        self, subscriber_client, stripe_user
    ):
        items = list(stripe_user.current_subscription_items)
        assert len(items) == 1
        assert items[0].subscription.status == "active"
        assert items[0].price.product_id is not None

    def test_current_subscription_is_the_one_the_stripe_user_holds(
        self, current_subscription, stripe_user
    ):
        Subscription = apps.get_model("drf_stripe", "Subscription")
        assert isinstance(current_subscription, Subscription)
        assert current_subscription.stripe_user_id == stripe_user.pk
        assert current_subscription.status == "active"
