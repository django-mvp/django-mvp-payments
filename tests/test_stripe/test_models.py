"""The Stripe app's local copy of a customer and their subscriptions."""

import pytest
from django.apps import apps
from django.core.management import call_command
from django.db import IntegrityError, transaction

from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
)

APP_MODELS = list(apps.get_app_config("mvp_payments_stripe").get_models())
APP_FIELDS = [
    pytest.param(field, id=f"{model.__name__}.{field.name}")
    for model in APP_MODELS
    for field in model._meta.get_fields()
    if not field.auto_created and field.concrete
]


class TestModelDeclarations:
    @pytest.mark.parametrize("field", APP_FIELDS)
    def test_every_field_states_its_verbose_name_and_help_text(self, field):
        # Django fills verbose_name in from the field's name when it is not given.
        assert field._verbose_name
        assert field.help_text

    def test_every_model_states_its_verbose_names(self):
        for model in APP_MODELS:
            assert model._meta.original_attrs["verbose_name"]
            assert model._meta.original_attrs["verbose_name_plural"]

    def test_the_app_has_exactly_a_customer_and_a_subscription(self):
        assert sorted(model.__name__ for model in APP_MODELS) == [
            "Customer",
            "Subscription",
        ]

    def test_tables_carry_the_app_label(self):
        assert sorted(model._meta.db_table for model in APP_MODELS) == [
            "mvp_payments_stripe_customer",
            "mvp_payments_stripe_subscription",
        ]

    @pytest.mark.django_db
    def test_the_models_are_fully_migrated(self):
        # --check exits non-zero when a model has changes no migration describes.
        call_command("makemigrations", "mvp_payments_stripe", "--check", "--dry-run")


@pytest.mark.django_db
class TestCustomerAndSubscriptionRows:
    def test_deleting_a_user_removes_their_customer_and_subscriptions(self):
        subscription = StripeSubscriptionFactory()
        user = subscription.customer.user
        other = StripeSubscriptionFactory()

        user.delete()

        customer_model = type(subscription.customer)
        assert not customer_model.objects.filter(pk=subscription.customer_id).exists()
        assert not type(subscription).objects.filter(pk=subscription.pk).exists()
        assert type(subscription).objects.filter(pk=other.pk).exists()

    def test_a_user_has_one_customer(self):
        customer = StripeCustomerFactory()

        with pytest.raises(IntegrityError), transaction.atomic():
            StripeCustomerFactory(user=customer.user)

    def test_a_user_may_have_several_subscriptions_on_one_customer(self):
        customer = StripeCustomerFactory()

        StripeSubscriptionFactory.create_batch(2, customer=customer)

        assert customer.subscriptions.count() == 2

    def test_subscriptions_come_latest_period_first(self):
        customer = StripeCustomerFactory()
        older = StripeSubscriptionFactory(
            customer=customer, current_period_end="2026-01-01T00:00:00Z"
        )
        newer = StripeSubscriptionFactory(
            customer=customer, current_period_end="2026-06-01T00:00:00Z"
        )

        assert list(customer.subscriptions.all()) == [newer, older]

    def test_a_status_stripe_adds_later_is_stored_as_reported(self):
        subscription = StripeSubscriptionFactory(status="a_status_not_yet_invented")

        subscription.refresh_from_db()

        assert subscription.status == "a_status_not_yet_invented"

    def test_a_zero_decimal_amount_is_stored_in_its_own_minor_unit(self):
        subscription = StripeSubscriptionFactory(amount=1500, currency="jpy")

        subscription.refresh_from_db()

        assert (subscription.amount, subscription.currency) == (1500, "jpy")
