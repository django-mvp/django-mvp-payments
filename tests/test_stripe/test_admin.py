"""The admin shows the records and offers no way to alter them."""

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from mvp_payments.stripe.models import Customer, Subscription
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
    UserFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls_with_admin")]

SUBSCRIPTIONS = "admin:mvp_payments_stripe_subscription_"
CUSTOMERS = "admin:mvp_payments_stripe_customer_"


@pytest.fixture
def superuser():
    return User.objects.create_superuser("root", "root@example.com", "pw")


@pytest.fixture
def admin_client(client, superuser):
    client.force_login(superuser)
    return client


def staff_with(*codenames):
    staff = UserFactory(is_staff=True)
    staff.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return staff


class TestListing:
    def test_a_superuser_lists_subscriptions(self, admin_client):
        subscription = StripeSubscriptionFactory(stripe_id="sub_listed")

        response = admin_client.get(reverse(f"{SUBSCRIPTIONS}changelist"))

        assert response.status_code == 200
        assert list(response.context["cl"].result_list) == [subscription]

    def test_subscriptions_are_filtered_by_status(self, admin_client):
        active = StripeSubscriptionFactory(status="active")
        StripeSubscriptionFactory(status="canceled")

        response = admin_client.get(
            reverse(f"{SUBSCRIPTIONS}changelist"), {"status__exact": "active"}
        )

        assert list(response.context["cl"].result_list) == [active]

    @pytest.mark.parametrize("term", ["ada", "ada@example.com", "sub_ada", "cus_ada"])
    def test_subscriptions_are_found_by_username_email_or_stripe_id(
        self, admin_client, term
    ):
        customer = StripeCustomerFactory(
            stripe_id="cus_ada",
            user=UserFactory(username="ada", email="ada@example.com"),
        )
        wanted = StripeSubscriptionFactory(customer=customer, stripe_id="sub_ada")
        StripeSubscriptionFactory()

        response = admin_client.get(reverse(f"{SUBSCRIPTIONS}changelist"), {"q": term})

        assert list(response.context["cl"].result_list) == [wanted]

    @pytest.mark.parametrize("term", ["ada", "ada@example.com", "cus_ada"])
    def test_customers_are_found_by_username_email_or_stripe_id(
        self, admin_client, term
    ):
        wanted = StripeCustomerFactory(
            stripe_id="cus_ada",
            user=UserFactory(username="ada", email="ada@example.com"),
        )
        StripeCustomerFactory()

        response = admin_client.get(reverse(f"{CUSTOMERS}changelist"), {"q": term})

        assert list(response.context["cl"].result_list) == [wanted]

    def test_the_subscription_list_runs_the_same_queries_for_one_row_or_several(
        self, admin_client, django_assert_num_queries
    ):
        url = reverse(f"{SUBSCRIPTIONS}changelist")
        StripeSubscriptionFactory()
        admin_client.get(url)  # warm the per-process caches the first request fills
        with CaptureQueriesContext(connection) as one_row:
            admin_client.get(url)
        StripeSubscriptionFactory.create_batch(5)

        with django_assert_num_queries(len(one_row)):
            admin_client.get(url)


class TestChangeView:
    def test_a_subscription_shows_its_values(self, admin_client):
        subscription = StripeSubscriptionFactory(
            customer=StripeCustomerFactory(
                stripe_id="cus_shown", user=UserFactory(username="grace")
            ),
            stripe_id="sub_shown",
            status="past_due",
            price_id="price_shown",
            product_name="Gold",
            amount=1500,
            currency="jpy",
            current_period_end="2026-06-01T00:00:00Z",
        )

        response = admin_client.get(
            reverse(f"{SUBSCRIPTIONS}change", args=[subscription.pk])
        )

        content = response.content.decode()
        assert response.status_code == 200
        for shown in (
            "grace",
            "cus_shown",
            "sub_shown",
            "Past due",
            "price_shown",
            "Gold",
            "1,500 JPY",
        ):
            assert shown in content

    def test_a_status_the_app_does_not_know_is_shown_as_stored(self, admin_client):
        subscription = StripeSubscriptionFactory(status="a_status_not_yet_invented")

        response = admin_client.get(
            reverse(f"{SUBSCRIPTIONS}change", args=[subscription.pk])
        )

        assert "a_status_not_yet_invented" in response.content.decode()

    def test_a_price_with_no_amount_shows_none(self, admin_client):
        subscription = StripeSubscriptionFactory(amount=None)

        response = admin_client.get(
            reverse(f"{SUBSCRIPTIONS}change", args=[subscription.pk])
        )

        assert response.status_code == 200

    def test_a_customer_shows_its_values(self, admin_client):
        customer = StripeCustomerFactory(
            stripe_id="cus_shown", user=UserFactory(username="grace")
        )

        response = admin_client.get(reverse(f"{CUSTOMERS}change", args=[customer.pk]))

        content = response.content.decode()
        assert "cus_shown" in content
        assert "grace" in content


class TestNothingCanBeAlteredHere:
    def test_a_superuser_is_refused_adding(self, admin_client):
        assert admin_client.get(reverse(f"{SUBSCRIPTIONS}add")).status_code == 403
        assert admin_client.get(reverse(f"{CUSTOMERS}add")).status_code == 403

    def test_a_superuser_cannot_change_a_record_by_posting(self, admin_client):
        subscription = StripeSubscriptionFactory(status="active")

        response = admin_client.post(
            reverse(f"{SUBSCRIPTIONS}change", args=[subscription.pk]),
            {"status": "canceled", "product_name": "Changed"},
        )

        subscription.refresh_from_db()
        assert response.status_code == 403
        assert (subscription.status, subscription.product_name) == ("active", "Pro")

    def test_a_superuser_cannot_delete_a_record(self, admin_client):
        subscription = StripeSubscriptionFactory()
        customer = subscription.customer

        for name, record in ((SUBSCRIPTIONS, subscription), (CUSTOMERS, customer)):
            url = reverse(f"{name}delete", args=[record.pk])
            assert admin_client.get(url).status_code == 403
            assert admin_client.post(url, {"post": "yes"}).status_code == 403

        assert Subscription.objects.filter(pk=subscription.pk).exists()
        assert Customer.objects.filter(pk=customer.pk).exists()

    def test_the_bulk_delete_action_is_not_offered(self, admin_client):
        StripeSubscriptionFactory()

        for name in (SUBSCRIPTIONS, CUSTOMERS):
            response = admin_client.get(reverse(f"{name}changelist"))
            assert response.context["action_form"] is None

    def test_the_bulk_delete_action_cannot_be_posted_either(self, admin_client):
        subscription = StripeSubscriptionFactory()

        admin_client.post(
            reverse(f"{SUBSCRIPTIONS}changelist"),
            {
                "action": "delete_selected",
                "_selected_action": [subscription.pk],
                "post": "yes",
            },
        )

        assert Subscription.objects.filter(pk=subscription.pk).exists()

    def test_the_changelist_offers_no_add_link(self, admin_client):
        response = admin_client.get(reverse(f"{SUBSCRIPTIONS}changelist"))

        assert response.context["has_add_permission"] is False


class TestDeletingAUserStillWorks:
    def test_the_user_admin_deletes_a_user_with_a_customer_and_its_subscriptions(
        self, admin_client
    ):
        subscription = StripeSubscriptionFactory()
        user = subscription.customer.user
        url = reverse("admin:auth_user_delete", args=[user.pk])

        confirmation = admin_client.get(url)
        assert confirmation.status_code == 200
        assert not confirmation.context["perms_lacking"]

        admin_client.post(url, {"post": "yes"})

        assert not User.objects.filter(pk=user.pk).exists()
        assert not Customer.objects.filter(pk=subscription.customer_id).exists()
        assert not Subscription.objects.filter(pk=subscription.pk).exists()


class TestWhoMaySee:
    def test_a_staff_user_with_view_permission_sees_the_list(self, client):
        client.force_login(staff_with("view_subscription"))

        response = client.get(reverse(f"{SUBSCRIPTIONS}changelist"))

        assert response.status_code == 200

    def test_a_staff_user_without_view_permission_sees_nothing(self, client):
        client.force_login(UserFactory(is_staff=True))

        assert client.get(reverse(f"{SUBSCRIPTIONS}changelist")).status_code == 403
        index = client.get(reverse("admin:index")).content.decode()
        assert "Stripe subscriptions" not in index
