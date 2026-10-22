"""The webhook: verify the signature, then fetch the current state from Stripe."""

import pytest
from django.urls import reverse

from mvp_payments.stripe.models import Customer, Subscription
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
    UserFactory,
)
from tests.stripe_fake import (
    WEBHOOK_SECRET,
    checkout_session_payload,
    customer_payload,
    event_payload,
    product_payload,
    sign_webhook,
    subscription_payload,
)


@pytest.fixture
def url():
    return reverse("payments:stripe-webhook")


@pytest.fixture
def deliver(client, url):
    """Post a webhook body, signed unless told otherwise."""

    def post(payload, signature=None, **headers):
        if signature is None:
            signature = sign_webhook(payload)
        return client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature,
            **headers,
        )

    return post


def stripe_now_holds(fake, customer_id, *subscriptions):
    fake.respond("GET", f"/v1/customers/{customer_id}", customer_payload(customer_id))
    fake.respond_with_list("/v1/subscriptions", list(subscriptions))
    fake.respond("GET", "/v1/products/prod_1", product_payload("prod_1", "Pro"))


def subscription_event(kind, subscription_id="sub_1", customer="cus_1", **fields):
    return event_payload(
        f"customer.subscription.{kind}",
        subscription_payload(subscription_id, customer, **fields),
    )


@pytest.mark.django_db
class TestWebhookVerification:
    @pytest.fixture
    def recorded(self):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer, stripe_id="sub_1", status="active")
        return customer

    def assert_nothing_changed(self, stripe_fake):
        assert Subscription.objects.get().status == "active"
        assert stripe_fake.requests == []

    def test_a_signed_event_is_acknowledged_with_an_empty_body(
        self, deliver, stripe_fake
    ):
        response = deliver(event_payload("ping", {"object": "ping"}))

        assert (response.status_code, response.content) == (200, b"")

    def test_an_unsigned_request_is_refused(self, client, url, recorded, stripe_fake):
        payload = subscription_event("updated", status="canceled")

        response = client.post(url, data=payload, content_type="application/json")

        assert (response.status_code, response.content) == (400, b"")
        self.assert_nothing_changed(stripe_fake)

    def test_a_signature_made_with_another_secret_is_refused(
        self, deliver, recorded, stripe_fake
    ):
        payload = subscription_event("updated", status="canceled")

        response = deliver(payload, sign_webhook(payload, secret="whsec_someone_else"))

        assert response.status_code == 400
        self.assert_nothing_changed(stripe_fake)

    def test_a_body_changed_after_signing_is_refused(
        self, deliver, recorded, stripe_fake
    ):
        signature = sign_webhook(subscription_event("updated"))

        response = deliver(subscription_event("deleted"), signature)

        assert response.status_code == 400
        self.assert_nothing_changed(stripe_fake)

    def test_an_expired_signature_is_refused(self, deliver, recorded, stripe_fake):
        payload = subscription_event("updated", status="canceled")

        response = deliver(payload, sign_webhook(payload, timestamp=1_000_000_000))

        assert response.status_code == 400
        self.assert_nothing_changed(stripe_fake)

    def test_a_body_that_is_not_json_is_refused_not_an_error(
        self, deliver, recorded, stripe_fake
    ):
        response = deliver("not json at all")

        assert response.status_code == 400
        self.assert_nothing_changed(stripe_fake)

    def test_a_webhook_signed_with_the_old_secret_is_refused_once_it_is_rotated(
        self, deliver, settings, recorded, stripe_fake
    ):
        payload = subscription_event("updated", status="canceled")
        settings.MVP_PAYMENTS = {
            **settings.MVP_PAYMENTS,
            "STRIPE_WEBHOOK_SECRET": "whsec_rotated",
        }

        response = deliver(payload, sign_webhook(payload, secret=WEBHOOK_SECRET))

        assert response.status_code == 400
        self.assert_nothing_changed(stripe_fake)

    @pytest.mark.parametrize("secret", ["", None])
    def test_an_unset_secret_accepts_nothing_even_if_signed_with_an_empty_key(
        self, deliver, settings, recorded, stripe_fake, secret
    ):
        payload = subscription_event("updated", status="canceled")
        settings.MVP_PAYMENTS = {
            **settings.MVP_PAYMENTS,
            "STRIPE_WEBHOOK_SECRET": secret,
        }

        response = deliver(payload, sign_webhook(payload, secret=""))

        assert response.status_code == 500
        self.assert_nothing_changed(stripe_fake)

    def test_a_get_is_refused(self, client, url):
        assert client.get(url).status_code == 405

    def test_the_view_needs_no_csrf_token(self, url, recorded):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        payload = subscription_event("updated")

        response = strict.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=sign_webhook(payload),
        )

        assert response.status_code != 403


@pytest.mark.django_db
class TestWebhookEvents:
    @pytest.mark.parametrize("kind", ["created", "updated", "deleted", "paused"])
    def test_a_subscription_event_records_what_stripe_holds_now(
        self, deliver, stripe_fake, kind
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer, stripe_id="sub_1", status="active")
        stripe_now_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", status="past_due"),
        )

        # The event claims a different state: it is a prompt, not a payload to trust.
        response = deliver(subscription_event(kind, status="active"))

        assert response.status_code == 200
        assert Subscription.objects.get().status == "past_due"

    def test_a_deleted_customer_event_removes_the_customer(self, deliver, stripe_fake):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer)
        stripe_fake.respond_with_error("GET", "/v1/customers/cus_1", "resource_missing")

        response = deliver(event_payload("customer.deleted", customer_payload("cus_1")))

        assert response.status_code == 200
        assert Customer.objects.count() == 0
        assert Subscription.objects.count() == 0

    def test_a_completed_checkout_records_the_customer_and_subscription(
        self, deliver, stripe_fake
    ):
        user = UserFactory()
        stripe_fake.respond(
            "GET",
            "/v1/checkout/sessions/cs_1",
            checkout_session_payload(
                "cs_1",
                client_reference_id=Customer.client_reference(user),
                customer="cus_new",
            ),
        )
        stripe_now_holds(
            stripe_fake, "cus_new", subscription_payload("sub_new", "cus_new")
        )

        response = deliver(
            event_payload(
                "checkout.session.completed",
                checkout_session_payload(
                    "cs_1", client_reference_id="ignored", customer="ignored"
                ),
            )
        )

        assert response.status_code == 200
        assert Customer.objects.get().user == user
        assert Subscription.objects.get().stripe_id == "sub_new"

    def test_a_checkout_that_cannot_be_tied_to_a_user_records_nothing(
        self, deliver, stripe_fake
    ):
        stripe_fake.respond(
            "GET",
            "/v1/checkout/sessions/cs_1",
            checkout_session_payload(
                "cs_1", client_reference_id="1", customer="cus_stranger"
            ),
        )

        response = deliver(
            event_payload(
                "checkout.session.completed",
                checkout_session_payload("cs_1", client_reference_id="1", customer="x"),
            )
        )

        assert response.status_code == 200
        assert Customer.objects.count() == 0

    def test_a_repeated_event_leaves_the_same_rows(self, deliver, stripe_fake):
        StripeCustomerFactory(stripe_id="cus_1")
        stripe_now_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", status="trialing"),
        )
        payload = subscription_event("created")

        deliver(payload)
        first = list(Subscription.objects.values_list("stripe_id", "status"))
        deliver(payload)

        assert list(Subscription.objects.values_list("stripe_id", "status")) == first
        assert first == [("sub_1", "trialing")]

    def test_a_late_event_after_a_newer_one_leaves_the_current_state(
        self, deliver, stripe_fake
    ):
        StripeCustomerFactory(stripe_id="cus_1")
        stripe_now_holds(
            stripe_fake,
            "cus_1",
            subscription_payload("sub_1", "cus_1", status="canceled"),
        )

        deliver(subscription_event("deleted", status="canceled"))
        deliver(subscription_event("created", status="incomplete"))
        deliver(subscription_event("updated", status="active"))

        assert list(Subscription.objects.values_list("stripe_id", "status")) == [
            ("sub_1", "canceled")
        ]

    def test_an_event_about_an_object_the_app_does_not_keep_is_acknowledged(
        self, deliver, stripe_fake
    ):
        StripeCustomerFactory(stripe_id="cus_1")

        response = deliver(
            event_payload("invoice.paid", {"id": "in_1", "object": "invoice"})
        )

        assert response.status_code == 200
        assert stripe_fake.requests == []

    def test_an_event_about_a_customer_nobody_recorded_is_acknowledged(
        self, deliver, stripe_fake
    ):
        response = deliver(subscription_event("updated", customer="cus_stranger"))

        assert response.status_code == 200
        assert Customer.objects.count() == 0
        assert stripe_fake.requests == []

    def test_stripe_being_unreachable_is_answered_with_a_failure_and_changes_nothing(
        self, deliver, stripe_fake
    ):
        customer = StripeCustomerFactory(stripe_id="cus_1")
        StripeSubscriptionFactory(customer=customer, status="active")
        stripe_fake.respond("GET", "/v1/customers/cus_1", customer_payload("cus_1"))
        stripe_fake.become_unreachable("GET", "/v1/subscriptions")

        response = deliver(subscription_event("updated", status="canceled"))

        assert (response.status_code, response.content) == (500, b"")
        assert Subscription.objects.get().status == "active"

    def test_a_checkout_that_fails_part_way_leaves_no_customer_behind(
        self, deliver, stripe_fake
    ):
        user = UserFactory()
        stripe_fake.respond(
            "GET",
            "/v1/checkout/sessions/cs_1",
            checkout_session_payload(
                "cs_1",
                client_reference_id=Customer.client_reference(user),
                customer="cus_new",
            ),
        )
        stripe_fake.become_unreachable("GET", "/v1/customers/cus_new")

        response = deliver(
            event_payload(
                "checkout.session.completed",
                checkout_session_payload("cs_1", client_reference_id="x", customer="x"),
            )
        )

        assert response.status_code == 500
        assert Customer.objects.count() == 0
