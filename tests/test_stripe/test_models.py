"""The Stripe app's local copy of a customer and their subscriptions."""

from datetime import UTC, datetime

import pytest
import stripe
from django.apps import apps
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext

from mvp_payments.stripe.models import Customer, Subscription
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
)
from tests.stripe_fake import (
    customer_payload,
    product_payload,
    subscription_payload,
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


def stripe_holds(fake, customer_id, *subscriptions, products=None):
    """Make the fake Stripe hold a customer, their subscriptions and the products."""
    fake.respond("GET", f"/v1/customers/{customer_id}", customer_payload(customer_id))
    fake.respond_with_list("/v1/subscriptions", list(subscriptions))
    for product_id, name in (products or {}).items():
        fake.respond(
            "GET", f"/v1/products/{product_id}", product_payload(product_id, name)
        )


@pytest.mark.django_db
class TestCustomerSync:
    def test_a_subscription_is_recorded_with_everything_stripe_holds(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload(
                "sub_1",
                "cus_1",
                status="trialing",
                price_id="price_pro",
                product="prod_pro",
                amount=2500,
                currency="gbp",
                interval="year",
                interval_count=2,
                period_start=1_790_000_000,
                period_end=1_792_592_000,
                cancel_at_period_end=True,
                ended_at=1_795_000_000,
            ),
            products={"prod_pro": "Pro plan"},
        )

        customer.sync()

        recorded = Subscription.objects.get()
        assert (
            recorded.customer,
            recorded.stripe_id,
            recorded.status,
            recorded.price_id,
            recorded.product_name,
            recorded.amount,
            recorded.currency,
            recorded.interval,
            recorded.interval_count,
            recorded.current_period_start,
            recorded.current_period_end,
            recorded.cancel_at_period_end,
            recorded.ended_at,
        ) == (
            customer,
            "sub_1",
            "trialing",
            "price_pro",
            "Pro plan",
            2500,
            "gbp",
            "year",
            2,
            datetime.fromtimestamp(1_790_000_000, tz=UTC),
            datetime.fromtimestamp(1_792_592_000, tz=UTC),
            True,
            datetime.fromtimestamp(1_795_000_000, tz=UTC),
        )

    def test_every_subscription_is_asked_for_whatever_its_status(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(stripe_fake, "cus_1")

        customer.sync()

        _, _, params = next(
            r for r in stripe_fake.requests if r[1] == "/v1/subscriptions"
        )
        assert params["customer"] == ["cus_1"]
        assert params["status"] == ["all"]
        assert "expand[]" not in params

    def test_a_product_shared_by_two_subscriptions_is_fetched_once(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", product="prod_a"),
            subscription_payload("sub_2", "cus_1", product="prod_a"),
            products={"prod_a": "Shared"},
        )

        customer.sync()

        assert stripe_fake.paths("GET").count("/v1/products/prod_a") == 1
        assert set(Subscription.objects.values_list("product_name", flat=True)) == {
            "Shared"
        }

    def test_a_change_at_stripe_is_followed_on_the_same_row(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        existing = StripeSubscriptionFactory(
            customer=customer, stripe_id="sub_1", status="active", price_id="price_old"
        )
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload(
                "sub_1",
                "cus_1",
                status="past_due",
                price_id="price_new",
                product="prod_new",
                cancel_at_period_end=True,
            ),
            products={"prod_new": "New plan"},
        )

        customer.sync()

        existing.refresh_from_db()
        assert (
            existing.status,
            existing.price_id,
            existing.product_name,
            existing.cancel_at_period_end,
        ) == ("past_due", "price_new", "New plan", True)
        assert Subscription.objects.count() == 1

    def test_a_subscription_stripe_reports_as_ended_is_kept_with_that_status(
        self, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer, stripe_id="sub_1", status="active")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload(
                "sub_1", "cus_1", status="canceled", ended_at=1_795_000_000
            ),
            products={"prod_1": "Pro"},
        )

        customer.sync()

        kept = Subscription.objects.get(stripe_id="sub_1")
        assert kept.status == "canceled"
        assert kept.ended_at == datetime.fromtimestamp(1_795_000_000, tz=UTC)

    def test_a_row_stripe_no_longer_returns_is_deleted(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer, stripe_id="sub_gone")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_kept", "cus_1"),
            products={"prod_1": "Pro"},
        )

        customer.sync()

        assert list(Subscription.objects.values_list("stripe_id", flat=True)) == [
            "sub_kept"
        ]

    def test_another_customers_rows_are_left_alone(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        other = StripeSubscriptionFactory()
        stripe_holds(stripe_fake, "cus_1")

        customer.sync()

        assert Subscription.objects.filter(pk=other.pk).exists()

    def test_syncing_twice_leaves_the_same_rows(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1"),
            products={"prod_1": "Pro"},
        )

        customer.sync()
        first = list(Subscription.objects.values())
        customer.sync()

        second = list(Subscription.objects.values())
        assert [{k: v for k, v in row.items() if k != "updated"} for row in second] == [
            {k: v for k, v in row.items() if k != "updated"} for row in first
        ]

    def test_a_zero_decimal_currency_is_recorded_as_reported(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", amount=1500, currency="jpy"),
            products={"prod_1": "Pro"},
        )

        customer.sync()

        recorded = Subscription.objects.get()
        assert (recorded.amount, recorded.currency) == (1500, "jpy")

    def test_a_price_with_no_unit_amount_is_recorded_with_none(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", amount=None),
            products={"prod_1": "Pro"},
        )

        customer.sync()

        assert Subscription.objects.get().amount is None

    def test_a_status_the_app_does_not_know_is_stored_as_reported(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", status="a_status_not_yet_invented"),
            products={"prod_1": "Pro"},
        )

        customer.sync()

        assert Subscription.objects.get().status == "a_status_not_yet_invented"

    def test_a_customer_stripe_reports_deleted_is_removed_with_its_subscriptions(
        self, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer)
        stripe_fake.respond(
            "GET",
            "/v1/customers/cus_1",
            {"id": "cus_1", "object": "customer", "deleted": True},
        )

        customer.sync()

        assert not Customer.objects.filter(pk=customer.pk).exists()
        assert Subscription.objects.count() == 0
        assert "/v1/subscriptions" not in stripe_fake.paths()

    def test_a_customer_stripe_no_longer_has_is_removed_with_its_subscriptions(
        self, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer)
        stripe_fake.respond_with_error("GET", "/v1/customers/cus_1", "resource_missing")

        customer.sync()

        assert not Customer.objects.filter(pk=customer.pk).exists()
        assert Subscription.objects.count() == 0

    def test_any_other_stripe_error_propagates_and_changes_nothing(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        kept = StripeSubscriptionFactory(customer=customer, status="active")
        stripe_fake.respond("GET", "/v1/customers/cus_1", customer_payload("cus_1"))
        stripe_fake.become_unreachable("GET", "/v1/subscriptions")

        with pytest.raises(stripe.StripeError):
            customer.sync()

        kept.refresh_from_db()
        assert kept.status == "active"

    def test_an_error_other_than_a_missing_customer_does_not_delete_it(
        self, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_fake.respond_with_error(
            "GET", "/v1/customers/cus_1", "api_key_expired", status=401
        )

        with pytest.raises(stripe.StripeError):
            customer.sync()

        assert Customer.objects.filter(pk=customer.pk).exists()

    def test_the_customer_row_is_re_read_before_stripe_is_asked_anything(
        self, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(stripe_fake, "cus_1")

        with CaptureQueriesContext(connection) as queries:
            customer.sync()

        first = next(q["sql"] for q in queries if not q["sql"].startswith("SAVEPOINT"))
        assert first.startswith("SELECT") and "mvp_payments_stripe_customer" in first

    def test_a_customer_deleted_meanwhile_is_a_quiet_no_op(self, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        Customer.objects.filter(pk=customer.pk).delete()

        customer.sync()

        assert stripe_fake.requests == []
