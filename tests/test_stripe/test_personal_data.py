"""The Stripe app's records, as the kinds django-mvp-compliance reads and deletes."""

from datetime import UTC, datetime

import pytest
from mvp_compliance.deletion import delete_account
from mvp_compliance.exceptions import AccountDeletionError
from mvp_compliance.personal_data import deletion_offered, get_personal_data

from mvp_payments.stripe.models import Customer, Subscription
from mvp_payments.stripe.personal_data import StripeCustomer, StripeSubscriptions
from tests.factories import StripeCustomerFactory, StripeSubscriptionFactory

KINDS = [
    "mvp_payments.stripe.personal_data.StripeCustomer",
    "mvp_payments.stripe.personal_data.StripeSubscriptions",
]


def stripe_deletes(fake, customer_id):
    """Make the fake Stripe delete ``customer_id`` when asked."""
    fake.respond(
        "DELETE",
        f"/v1/customers/{customer_id}",
        {"id": customer_id, "object": "customer", "deleted": True},
    )


@pytest.fixture
def subscribed(stripe_customer):
    return StripeSubscriptionFactory(
        customer=stripe_customer,
        stripe_id="sub_1",
        status="active",
        product_name="Pro plan",
        amount=2500,
        currency="gbp",
        current_period_end=datetime(2026, 11, 1, tzinfo=UTC),
    )


@pytest.mark.django_db
class TestStripeCustomer:
    def test_a_project_declares_both_kinds_and_deletion_is_offered(self, settings):
        settings.MVP_COMPLIANCE_PERSONAL_DATA = KINDS

        kinds = get_personal_data()

        assert [type(kind) for kind in kinds] == [StripeCustomer, StripeSubscriptions]
        assert deletion_offered()

    def test_the_copy_holds_the_persons_customer_and_no_one_elses(
        self, user, stripe_customer
    ):
        StripeCustomerFactory()

        section = StripeCustomer().collect(user)

        assert section.single
        assert [column for column, _ in section.columns] == ["stripe_id", "created"]
        assert section.rows == ((stripe_customer.stripe_id, stripe_customer.created),)

    def test_a_person_with_no_customer_has_an_empty_section(self, user):
        assert StripeCustomer().collect(user).rows == ()

    def test_erasing_deletes_the_customer_at_stripe_and_here(
        self, user, subscribed, stripe_fake
    ):
        customer_id = subscribed.customer.stripe_id
        stripe_deletes(stripe_fake, customer_id)
        other = StripeSubscriptionFactory()

        StripeCustomer().erase(user)

        assert stripe_fake.paths("DELETE") == [f"/v1/customers/{customer_id}"]
        assert not Customer.objects.filter(user=user).exists()
        assert list(Subscription.objects.all()) == [other]

    def test_erasing_a_person_with_no_customer_asks_stripe_nothing(
        self, user, stripe_fake
    ):
        StripeCustomer().erase(user)

        assert stripe_fake.requests == []


@pytest.mark.django_db
class TestStripeSubscriptions:
    def test_the_copy_holds_every_subscription_of_the_person_and_no_one_elses(
        self, user, subscribed
    ):
        ended = StripeSubscriptionFactory(
            customer=subscribed.customer, stripe_id="sub_0", status="canceled"
        )
        StripeSubscriptionFactory()

        section = StripeSubscriptions().collect(user)

        names = [column for column, _ in section.columns]
        recorded = {row[names.index("stripe_id")] for row in section.rows}
        assert recorded == {subscribed.stripe_id, ended.stripe_id}

    def test_each_subscription_carries_what_the_app_recorded(self, user, subscribed):
        section = StripeSubscriptions().collect(user)

        (row,) = section.rows
        values = dict(zip([column for column, _ in section.columns], row, strict=True))
        assert values["product_name"] == "Pro plan"
        assert values["status"].value == "active"
        assert (values["amount"], values["currency"]) == (2500, "gbp")
        assert values["current_period_end"] == subscribed.current_period_end

    def test_erasing_deletes_the_customer_at_stripe_and_here(
        self, user, subscribed, stripe_fake
    ):
        stripe_deletes(stripe_fake, subscribed.customer.stripe_id)

        StripeSubscriptions().erase(user)

        assert stripe_fake.paths("DELETE") == [
            f"/v1/customers/{subscribed.customer.stripe_id}"
        ]
        assert not Subscription.objects.exists()


@pytest.mark.django_db
class TestDeletingAnAccount:
    def test_stripe_is_asked_once_and_the_account_goes(
        self, user, subscribed, stripe_fake
    ):
        stripe_deletes(stripe_fake, subscribed.customer.stripe_id)

        delete_account(user, [StripeCustomer(), StripeSubscriptions()])

        assert stripe_fake.paths("DELETE") == [
            f"/v1/customers/{subscribed.customer.stripe_id}"
        ]
        assert not type(user).objects.filter(username=user.username).exists()

    def test_when_stripe_cannot_be_reached_nothing_is_deleted(
        self, user, subscribed, stripe_fake
    ):
        stripe_fake.become_unreachable(
            "DELETE", f"/v1/customers/{subscribed.customer.stripe_id}"
        )

        with pytest.raises(AccountDeletionError):
            delete_account(user, [StripeCustomer(), StripeSubscriptions()])

        assert type(user).objects.filter(pk=user.pk).exists()
        assert Subscription.objects.filter(pk=subscribed.pk).exists()
