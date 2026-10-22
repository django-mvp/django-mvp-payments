"""The Stripe app's local copy of a customer and their subscriptions."""

import re
from datetime import UTC, datetime

import pytest
import stripe
from django.apps import apps
from django.contrib.auth.models import AnonymousUser, User
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext

from mvp_payments.stripe.models import Customer, Subscription
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
    UserFactory,
)
from tests.stripe_fake import (
    checkout_session_payload,
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


@pytest.mark.django_db
class TestCustomerClientReference:
    def test_the_reference_uses_only_characters_the_pricing_table_accepts(self):
        reference = Customer.client_reference(UserFactory())

        assert re.fullmatch(r"[A-Za-z0-9_-]+", reference)

    def test_the_reference_starts_with_the_users_primary_key(self):
        user = UserFactory()

        assert Customer.client_reference(user).startswith(f"{user.pk}_")

    def test_two_users_get_different_references(self):
        first, second = UserFactory(), UserFactory()

        assert Customer.client_reference(first) != Customer.client_reference(second)

    def test_the_same_user_always_gets_the_same_reference(self):
        user = UserFactory()

        assert Customer.client_reference(user) == Customer.client_reference(user)


def completed_checkout(fake, reference, customer="cus_new", mode="subscription"):
    fake.respond(
        "GET",
        "/v1/checkout/sessions/cs_1",
        checkout_session_payload(
            "cs_1", client_reference_id=reference, customer=customer, mode=mode
        ),
    )


@pytest.mark.django_db
class TestCustomerFromCheckout:
    def test_a_valid_reference_ties_a_new_customer_to_the_user(self, stripe_fake):
        user = UserFactory()
        completed_checkout(stripe_fake, Customer.client_reference(user))

        customer = Customer.from_checkout("cs_1")

        assert (customer.user, customer.stripe_id) == (user, "cus_new")
        assert Customer.objects.get().pk == customer.pk

    def test_a_user_who_subscribes_again_keeps_the_same_customer(self, stripe_fake):
        existing = StripeCustomerFactory(stripe_id="cus_new")
        completed_checkout(stripe_fake, Customer.client_reference(existing.user))

        customer = Customer.from_checkout("cs_1")

        assert customer == existing
        assert Customer.objects.count() == 1

    def test_a_second_customer_for_a_user_is_refused_and_logged_with_both_ids(
        self, stripe_fake, caplog
    ):
        existing = StripeCustomerFactory(stripe_id="cus_first")
        completed_checkout(
            stripe_fake, Customer.client_reference(existing.user), customer="cus_second"
        )

        with caplog.at_level("ERROR"):
            result = Customer.from_checkout("cs_1")

        assert result is None
        assert [c.stripe_id for c in Customer.objects.all()] == ["cus_first"]
        messages = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
        assert any("cus_first" in m and "cus_second" in m for m in messages)

    def test_a_customer_already_recorded_for_another_user_is_not_taken_over(
        self, stripe_fake
    ):
        owner = StripeCustomerFactory(stripe_id="cus_new")
        newcomer = UserFactory()
        completed_checkout(stripe_fake, Customer.client_reference(newcomer))

        result = Customer.from_checkout("cs_1")

        assert result is None
        assert Customer.objects.get().user == owner.user

    def test_a_bare_primary_key_ties_nobody(self, stripe_fake):
        user = UserFactory()
        completed_checkout(stripe_fake, str(user.pk))

        assert Customer.from_checkout("cs_1") is None
        assert Customer.objects.count() == 0

    def test_a_tampered_signature_ties_nobody(self, stripe_fake):
        user = UserFactory()
        reference = Customer.client_reference(user)
        completed_checkout(
            stripe_fake, reference[:-1] + ("0" if reference[-1] != "0" else "1")
        )

        assert Customer.from_checkout("cs_1") is None
        assert Customer.objects.count() == 0

    def test_another_users_signature_ties_nobody(self, stripe_fake):
        attacker, victim = UserFactory(), UserFactory()
        signature = Customer.client_reference(attacker).partition("_")[2]
        completed_checkout(stripe_fake, f"{victim.pk}_{signature}")

        assert Customer.from_checkout("cs_1") is None
        assert Customer.objects.count() == 0

    def test_a_reference_for_a_user_who_no_longer_exists_ties_nobody(self, stripe_fake):
        user = UserFactory()
        reference = Customer.client_reference(user)
        user.delete()
        completed_checkout(stripe_fake, reference)

        assert Customer.from_checkout("cs_1") is None
        assert Customer.objects.count() == 0

    @pytest.mark.parametrize("reference", [None, ""])
    def test_a_session_with_no_reference_ties_nobody(self, stripe_fake, reference):
        completed_checkout(stripe_fake, reference)

        assert Customer.from_checkout("cs_1") is None

    def test_a_session_with_no_customer_ties_nobody(self, stripe_fake):
        completed_checkout(
            stripe_fake, Customer.client_reference(UserFactory()), customer=None
        )

        assert Customer.from_checkout("cs_1") is None
        assert Customer.objects.count() == 0

    @pytest.mark.parametrize("mode", ["payment", "setup"])
    def test_a_session_not_in_subscription_mode_ties_nobody(self, stripe_fake, mode):
        completed_checkout(
            stripe_fake, Customer.client_reference(UserFactory()), mode=mode
        )

        assert Customer.from_checkout("cs_1") is None
        assert Customer.objects.count() == 0

    def test_stripe_being_unreachable_is_raised(self, stripe_fake):
        stripe_fake.become_unreachable("GET", "/v1/checkout/sessions/cs_1")

        with pytest.raises(stripe.APIConnectionError):
            Customer.from_checkout("cs_1")


COUNTS_AS_SUBSCRIBED = {"active", "trialing"}
HAS_ENDED = {"canceled", "incomplete_expired"}


@pytest.mark.django_db
class TestSubscriptionQuerySet:
    @pytest.mark.parametrize(
        "status",
        [
            *Subscription.Status.values,
            pytest.param("a_status_not_yet_invented", id="unknown"),
        ],
    )
    def test_a_user_is_subscribed_for_exactly_the_statuses_that_count(self, status):
        subscription = StripeSubscriptionFactory(status=status)

        answer = (
            Subscription.objects.for_user(subscription.customer.user)
            .subscribed()
            .exists()
        )

        assert answer is (status in COUNTS_AS_SUBSCRIBED)

    @pytest.mark.parametrize(
        "status",
        [
            *Subscription.Status.values,
            pytest.param("a_status_not_yet_invented", id="unknown"),
        ],
    )
    def test_current_keeps_every_subscription_that_has_not_ended(self, status):
        subscription = StripeSubscriptionFactory(status=status)

        current = Subscription.objects.for_user(subscription.customer.user).current()

        assert current.exists() is (status not in HAS_ENDED)

    def test_a_subscription_set_to_cancel_at_period_end_still_counts(self):
        subscription = StripeSubscriptionFactory(
            status="active", cancel_at_period_end=True
        )

        assert Subscription.objects.for_user(subscription.customer.user).subscribed()

    def test_a_user_with_no_customer_is_not_subscribed(self):
        assert not Subscription.objects.for_user(UserFactory()).subscribed().exists()

    def test_a_user_with_a_customer_and_no_subscription_is_not_subscribed(self):
        customer = StripeCustomerFactory()

        assert not Subscription.objects.for_user(customer.user).subscribed().exists()

    def test_any_one_subscription_that_counts_is_enough(self):
        customer = StripeCustomerFactory()
        StripeSubscriptionFactory(customer=customer, status="canceled")
        StripeSubscriptionFactory(customer=customer, status="past_due")
        StripeSubscriptionFactory(customer=customer, status="trialing")

        assert Subscription.objects.for_user(customer.user).subscribed().exists()

    def test_several_subscriptions_none_of_which_count_do_not_add_up_to_one(self):
        customer = StripeCustomerFactory()
        StripeSubscriptionFactory(customer=customer, status="canceled")
        StripeSubscriptionFactory(customer=customer, status="unpaid")

        assert not Subscription.objects.for_user(customer.user).subscribed().exists()

    def test_anyone_not_signed_in_is_not_subscribed(self):
        StripeSubscriptionFactory()

        assert not Subscription.objects.for_user(AnonymousUser()).exists()

    def test_a_user_who_was_never_saved_is_not_subscribed(self):
        StripeSubscriptionFactory()

        assert not Subscription.objects.for_user(User()).exists()

    def test_only_the_named_users_subscriptions_are_returned(self):
        mine = StripeSubscriptionFactory()
        StripeSubscriptionFactory()

        assert list(Subscription.objects.for_user(mine.customer.user)) == [mine]

    def test_the_current_subscription_is_the_one_with_the_latest_period(self):
        customer = StripeCustomerFactory()
        StripeSubscriptionFactory(
            customer=customer, current_period_end="2026-01-01T00:00:00Z"
        )
        newest = StripeSubscriptionFactory(
            customer=customer, current_period_end="2026-06-01T00:00:00Z"
        )

        current = Subscription.objects.for_user(customer.user).subscribed().first()

        assert current == newest

    def test_there_is_no_current_subscription_when_none_counts(self):
        subscription = StripeSubscriptionFactory(status="canceled")

        current = (
            Subscription.objects.for_user(subscription.customer.user)
            .subscribed()
            .first()
        )

        assert current is None


@pytest.mark.django_db
class TestCustomerPortalUrl:
    def test_asks_stripe_for_a_portal_session_for_this_customer_and_returns_its_url(
        self, stripe_fake
    ):
        stripe_fake.respond(
            "POST",
            "/v1/billing_portal/sessions",
            {"id": "bps_1", "object": "billing_portal.session", "url": "https://x/p"},
        )
        customer = StripeCustomerFactory(stripe_id="cus_9")

        url = customer.portal_url("https://site.example/back/")

        assert url == "https://x/p"
        ((_, _, params),) = stripe_fake.requests
        assert params == {
            "customer": ["cus_9"],
            "return_url": ["https://site.example/back/"],
        }

    def test_a_flow_is_passed_through_to_stripe(self, stripe_fake):
        stripe_fake.respond(
            "POST",
            "/v1/billing_portal/sessions",
            {"id": "bps_1", "object": "billing_portal.session", "url": "https://x/p"},
        )
        customer = StripeCustomerFactory()

        customer.portal_url(
            "https://site.example/back/", {"type": "payment_method_update"}
        )

        ((_, _, params),) = stripe_fake.requests
        assert params["flow_data[type]"] == ["payment_method_update"]

    def test_a_stripe_failure_is_raised(self, stripe_fake):
        stripe_fake.become_unreachable("POST", "/v1/billing_portal/sessions")

        with pytest.raises(stripe.StripeError):
            StripeCustomerFactory().portal_url("https://site.example/back/")


@pytest.mark.django_db
class TestCustomerPlanChangeFlow:
    def test_a_customer_with_one_subscription_is_led_to_changing_that_one(self):
        customer = StripeCustomerFactory()
        subscription = StripeSubscriptionFactory(customer=customer, status="active")

        flow = customer.plan_change_flow("https://site.example/back/")

        assert flow == {
            "type": "subscription_update",
            "subscription_update": {"subscription": subscription.stripe_id},
            "after_completion": {
                "type": "redirect",
                "redirect": {"return_url": "https://site.example/back/"},
            },
        }

    def test_a_subscription_that_does_not_count_is_not_led_to(self):
        customer = StripeCustomerFactory()
        StripeSubscriptionFactory(customer=customer, status="canceled")

        assert customer.plan_change_flow("https://site.example/back/") is None

    def test_several_subscriptions_leave_the_choice_to_the_portal(self):
        customer = StripeCustomerFactory()
        StripeSubscriptionFactory(customer=customer, status="active")
        StripeSubscriptionFactory(customer=customer, status="trialing")

        assert customer.plan_change_flow("https://site.example/back/") is None


@pytest.mark.django_db
class TestCustomerForUser:
    def test_finds_the_users_own_customer(self, user):
        customer = StripeCustomerFactory(user=user)
        StripeCustomerFactory()

        assert Customer.for_user(user) == customer

    def test_a_user_with_no_customer_has_none(self, user):
        StripeCustomerFactory()

        assert Customer.for_user(user) is None

    def test_someone_not_signed_in_has_none(self):
        assert Customer.for_user(AnonymousUser()) is None
