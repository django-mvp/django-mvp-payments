"""The stripe_sync command: catch the records up after webhooks were missed."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from mvp_payments.stripe.models import Customer, Subscription
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
    UserFactory,
)
from tests.stripe_fake import customer_payload, product_payload, subscription_payload


def stripe_holds(fake, customer_id, *subscriptions):
    fake.respond("GET", f"/v1/customers/{customer_id}", customer_payload(customer_id))
    fake.respond_with_list("/v1/subscriptions", list(subscriptions))
    fake.respond("GET", "/v1/products/prod_1", product_payload("prod_1", "Pro"))


def run(*args):
    out = StringIO()
    call_command("stripe_sync", *args, stdout=out)
    return out.getvalue()


def rows():
    return sorted(
        Subscription.objects.values(
            "stripe_id", "customer__stripe_id", "status", "amount", "current_period_end"
        ),
        key=lambda row: row["stripe_id"],
    )


@pytest.mark.django_db
class TestStripeSyncCommand:
    def test_every_recorded_customer_is_brought_into_step_with_stripe(
        self, stripe_fake
    ):
        # The fake answers by path, so the two customers differ in whether Stripe has them.
        kept = StripeCustomerFactory(stripe_id="cus_1")
        gone = StripeCustomerFactory(stripe_id="cus_2")
        StripeSubscriptionFactory(customer=kept, stripe_id="sub_1", status="active")
        StripeSubscriptionFactory(customer=gone, stripe_id="sub_2", status="active")
        stripe_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", status="canceled"),
        )
        stripe_fake.respond_with_error("GET", "/v1/customers/cus_2", "resource_missing")

        run()

        assert dict(Subscription.objects.values_list("stripe_id", "status")) == {
            "sub_1": "canceled"
        }
        assert list(Customer.objects.values_list("stripe_id", flat=True)) == ["cus_1"]

    def test_a_customer_stripe_no_longer_has_is_left_with_no_subscription(
        self, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_gone")
        StripeSubscriptionFactory(customer=customer)
        stripe_fake.respond_with_error(
            "GET", "/v1/customers/cus_gone", "resource_missing"
        )

        run()

        assert not Customer.objects.filter(pk=customer.pk).exists()
        assert not Subscription.objects.exists()

    def test_a_second_run_changes_nothing(self, stripe_fake):
        StripeCustomerFactory(stripe_id="cus_1")
        stripe_holds(stripe_fake, "cus_1", subscription_payload("sub_1", "cus_1"))
        run()
        after_first = rows()

        run()

        assert rows() == after_first
        assert Subscription.objects.count() == 1

    def test_naming_a_user_syncs_only_that_users_customer(self, stripe_fake):
        named = StripeCustomerFactory(
            stripe_id="cus_named", user=UserFactory(username="ada")
        )
        StripeCustomerFactory(stripe_id="cus_other")
        stripe_holds(
            stripe_fake, "cus_named", subscription_payload("sub_n", "cus_named")
        )

        run("--user", "ada")

        assert stripe_fake.paths("GET").count("/v1/customers/cus_named") == 1
        assert "/v1/customers/cus_other" not in stripe_fake.paths()
        assert list(Subscription.objects.values_list("customer", flat=True)) == [
            named.pk
        ]

    def test_an_unknown_username_is_an_error_and_asks_stripe_nothing(self, stripe_fake):
        StripeCustomerFactory()

        with pytest.raises(CommandError, match="nobody"):
            run("--user", "nobody")

        assert stripe_fake.requests == []

    def test_a_user_with_no_customer_is_an_error(self, stripe_fake):
        UserFactory(username="grace")

        with pytest.raises(CommandError, match="grace"):
            run("--user", "grace")

    def test_it_says_how_many_customers_it_synced(self, stripe_fake):
        StripeCustomerFactory(stripe_id="cus_1")
        StripeCustomerFactory(stripe_id="cus_2")
        stripe_holds(stripe_fake, "cus_1")
        stripe_holds(stripe_fake, "cus_2")

        assert "2" in run()

    def test_with_no_customers_it_finishes_without_asking_stripe(self, stripe_fake):
        run()

        assert stripe_fake.requests == []

    def test_stripe_going_away_part_way_keeps_what_was_synced_and_says_how_many(
        self, stripe_fake
    ):
        StripeCustomerFactory(stripe_id="cus_1")
        StripeCustomerFactory(stripe_id="cus_2")
        StripeCustomerFactory(stripe_id="cus_3")
        stripe_holds(stripe_fake, "cus_1", subscription_payload("sub_1", "cus_1"))
        stripe_fake.become_unreachable("GET", "/v1/customers/cus_2")
        stripe_fake.respond_with_error("GET", "/v1/customers/cus_3", "resource_missing")

        with pytest.raises(CommandError, match="1 customer"):
            run()

        assert Subscription.objects.filter(stripe_id="sub_1").exists()
        assert Customer.objects.filter(stripe_id="cus_3").exists()

        # Stripe comes back: running it again finishes the rest.
        stripe_fake.respond_with_error("GET", "/v1/customers/cus_2", "resource_missing")
        run()
        assert list(Customer.objects.values_list("stripe_id", flat=True)) == ["cus_1"]
        assert Subscription.objects.filter(stripe_id="sub_1").exists()
