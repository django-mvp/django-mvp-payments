"""The webhook, and the handoffs to Stripe's billing portal."""

import logging

import pytest
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.urls import reverse
from django.views.debug import ExceptionReporter

from mvp_payments.stripe.catalogue import Catalogue
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
    price_payload,
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


@pytest.mark.django_db
class TestWebhookClearsTheCatalogue:
    @pytest.fixture
    def cached(self):
        cache.set(Catalogue.KEY, [{"id": "price_1"}], 3600)

    @pytest.mark.parametrize(
        "event_type",
        [
            "product.created",
            "product.updated",
            "product.deleted",
            "price.created",
            "price.updated",
            "price.deleted",
        ],
    )
    def test_a_verified_product_or_price_event_makes_the_next_read_ask_stripe(
        self, deliver, stripe_fake, cached, event_type
    ):
        response = deliver(event_payload(event_type, {"id": "x", "object": "price"}))

        assert response.status_code == 200
        assert cache.get(Catalogue.KEY) is None
        assert stripe_fake.requests == []

    def test_an_unverified_event_leaves_the_catalogue(
        self, client, url, stripe_fake, cached
    ):
        response = client.post(
            url,
            data=event_payload("price.updated", {"id": "x", "object": "price"}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=forged",
        )

        assert response.status_code == 400
        assert cache.get(Catalogue.KEY) == [{"id": "price_1"}]

    def test_an_event_that_is_neither_leaves_the_catalogue(
        self, deliver, stripe_fake, cached
    ):
        deliver(event_payload("ping", {"object": "ping"}))

        assert cache.get(Catalogue.KEY) == [{"id": "price_1"}]


@pytest.mark.django_db
class TestWebhookKeepsSecretsOut:
    @pytest.fixture
    def secrets(self, settings):
        return (settings.MVP_PAYMENTS["STRIPE_SECRET_KEY"], WEBHOOK_SECRET)

    def assert_no_secret_anywhere(self, response, caplog, secrets):
        text = response.content.decode() + caplog.text
        text += " ".join(
            f"{record.getMessage()} {record.exc_text}" for record in caplog.records
        )
        for secret in secrets:
            assert secret not in text

    def test_a_refused_request_leaks_neither_secret(
        self, deliver, caplog, secrets, stripe_fake
    ):
        caplog.set_level(logging.DEBUG)
        payload = subscription_event("updated")

        response = deliver(payload, sign_webhook(payload, secret="whsec_someone_else"))

        assert response.status_code == 400
        self.assert_no_secret_anywhere(response, caplog, secrets)

    def test_a_stripe_error_quoting_the_key_leaks_neither_secret(
        self, deliver, caplog, secrets, stripe_fake
    ):
        caplog.set_level(logging.DEBUG)
        StripeCustomerFactory(stripe_id="cus_1")
        # Stripe masks the middle of a key it repeats back, as its SDK logs the message.
        masked = f"{secrets[0][:8]}********{secrets[0][-4:]}"
        stripe_fake.respond_with_message_echoing("GET", "/v1/customers/cus_1", masked)

        response = deliver(subscription_event("updated"))

        assert response.status_code == 500
        self.assert_no_secret_anywhere(response, caplog, secrets)
        ours = [
            record.getMessage()
            for record in caplog.records
            if record.name.startswith("mvp_payments")
        ]
        assert ours
        assert not any(masked in message for message in ours)

    def test_an_unset_signing_secret_leaks_nothing(
        self, deliver, settings, caplog, secrets, stripe_fake
    ):
        caplog.set_level(logging.DEBUG)
        settings.MVP_PAYMENTS = {**settings.MVP_PAYMENTS, "STRIPE_WEBHOOK_SECRET": ""}

        response = deliver(subscription_event("updated"))

        assert response.status_code == 500
        self.assert_no_secret_anywhere(response, caplog, secrets)

    def test_a_handled_event_leaks_nothing(self, deliver, caplog, secrets, stripe_fake):
        caplog.set_level(logging.DEBUG)

        response = deliver(event_payload("ping", {"object": "ping"}))

        self.assert_no_secret_anywhere(response, caplog, secrets)

    def test_an_unexpected_failure_after_verifying_keeps_the_signing_secret_out_of_its_report(
        self, deliver, rf, stripe_fake
    ):
        """The report an admin email or an error tracker builds lists each frame's locals."""
        StripeCustomerFactory(stripe_id="cus_1")
        malformed = {**subscription_payload("sub_1", "cus_1")}
        del malformed["items"]
        stripe_now_holds(stripe_fake, "cus_1", malformed)

        with pytest.raises(KeyError) as raised:
            deliver(subscription_event("updated"))

        report = ExceptionReporter(
            rf.post("/"), raised.type, raised.value, raised.tb
        ).get_traceback_html()
        assert "webhook" in report
        assert WEBHOOK_SECRET not in report


PORTAL_PATH = "/v1/billing_portal/sessions"


@pytest.fixture
def portal_opens(stripe_fake):
    stripe_fake.respond(
        "POST",
        PORTAL_PATH,
        {
            "id": "bps_1",
            "object": "billing_portal.session",
            "url": "https://billing.example.com/session",
        },
    )
    return stripe_fake


def posted_to_the_portal(fake):
    return [params for method, path, params in fake.requests if path == PORTAL_PATH]


@pytest.mark.django_db
class TestBillingPortal:
    url = "/account/billing/stripe/billing-portal/"

    def test_is_mounted_with_the_packages_urls(self):
        assert reverse("payments:stripe-billing-portal") == self.url

    def test_a_customer_is_given_the_address_stripe_minted(
        self, portal_opens, client, user
    ):
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 200
        assert response.json() == {"url": "https://billing.example.com/session"}
        ((params,)) = posted_to_the_portal(portal_opens)
        assert params["customer"] == ["cus_mine"]

    def test_it_keeps_working_on_every_call_after_the_first(
        self, portal_opens, client, user
    ):
        StripeCustomerFactory(user=user)
        client.force_login(user)

        statuses = [client.post(self.url).status_code for _ in range(3)]

        assert statuses == [200, 200, 200]

    def test_stripe_is_asked_for_this_persons_own_customer_never_anothers(
        self, portal_opens, client, user
    ):
        StripeCustomerFactory(stripe_id="cus_somebody_else")
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        client.force_login(user)

        client.post(self.url)

        ((params,)) = posted_to_the_portal(portal_opens)
        assert params["customer"] == ["cus_mine"]

    def test_the_reader_is_sent_back_through_the_return_view_with_no_flow(
        self, portal_opens, client, user
    ):
        StripeCustomerFactory(user=user)
        client.force_login(user)

        client.post(self.url)

        ((params,)) = posted_to_the_portal(portal_opens)
        assert params["return_url"][0].endswith(
            reverse("payments:stripe-billing-return")
        )
        assert not any(key.startswith("flow_data") for key in params)

    def test_somebody_with_no_customer_gets_no_portal(self, portal_opens, client, user):
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 409
        assert portal_opens.requests == []

    def test_signing_in_is_required(self, portal_opens, client, db):
        response = client.post(self.url)

        assert response.status_code == 302
        assert portal_opens.requests == []

    def test_only_a_post_is_answered(self, portal_opens, client, user):
        StripeCustomerFactory(user=user)
        client.force_login(user)

        assert client.get(self.url).status_code == 405

    def test_stripe_being_unreachable_is_reported_without_its_message(
        self, stripe_fake, client, user, caplog
    ):
        StripeCustomerFactory(user=user)
        client.force_login(user)
        stripe_fake.respond_with_message_echoing(
            "POST", PORTAL_PATH, "sk_test_not_a_r********_key"
        )

        response = client.post(self.url)

        assert response.status_code == 502
        assert "sk_test" not in response.content.decode() + caplog.text


@pytest.mark.django_db
class TestPlanSwitch:
    url = "/account/billing/stripe/plan-switch/"

    def test_it_opens_the_plan_change_screen_for_the_persons_subscription(
        self, portal_opens, client, user
    ):
        customer = StripeCustomerFactory(user=user, stripe_id="cus_mine")
        subscription = StripeSubscriptionFactory(customer=customer, status="active")
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 200
        assert response.json() == {"url": "https://billing.example.com/session"}
        ((params,)) = posted_to_the_portal(portal_opens)
        assert params["customer"] == ["cus_mine"]
        assert params["flow_data[type]"] == ["subscription_update"]
        assert params["flow_data[subscription_update][subscription]"] == [
            subscription.stripe_id
        ]
        assert params["flow_data[after_completion][redirect][return_url]"][0].endswith(
            reverse("payments:stripe-billing-return")
        )

    def test_several_subscriptions_open_the_portal_to_choose_from(
        self, portal_opens, client, user
    ):
        customer = StripeCustomerFactory(user=user)
        StripeSubscriptionFactory(customer=customer, status="active")
        StripeSubscriptionFactory(customer=customer, status="trialing")
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 200
        ((params,)) = posted_to_the_portal(portal_opens)
        assert not any(key.startswith("flow_data") for key in params)

    def test_somebody_with_nothing_subscribed_has_nothing_to_switch(
        self, portal_opens, client, user
    ):
        customer = StripeCustomerFactory(user=user)
        StripeSubscriptionFactory(customer=customer, status="canceled")
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 409
        assert portal_opens.requests == []

    def test_somebody_with_no_customer_has_nothing_to_switch(
        self, portal_opens, client, user
    ):
        client.force_login(user)

        response = client.post(self.url)

        assert response.status_code == 409
        assert portal_opens.requests == []

    def test_signing_in_is_required(self, portal_opens, client, db):
        response = client.post(self.url)

        assert response.status_code == 302
        assert portal_opens.requests == []


@pytest.mark.django_db
class TestBillingReturn:
    url = "/account/billing/stripe/return/"

    def test_it_refreshes_from_stripe_then_shows_the_subscription_page(
        self, stripe_fake, client, user
    ):
        customer = StripeCustomerFactory(user=user, stripe_id="cus_mine")
        stripe_now_holds(
            stripe_fake, "cus_mine", subscription_payload("sub_new", "cus_mine")
        )
        client.force_login(user)

        response = client.get(self.url)

        assert response.status_code == 302
        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"
        assert list(customer.subscriptions.values_list("stripe_id", flat=True)) == [
            "sub_new"
        ]

    def test_somebody_with_no_customer_is_sent_on_without_asking_stripe(
        self, stripe_fake, client, user
    ):
        client.force_login(user)

        response = client.get(self.url)

        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"
        assert stripe_fake.requests == []

    def test_stripe_being_unreachable_still_sends_the_reader_on(
        self, stripe_fake, client, user
    ):
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        stripe_fake.become_unreachable("GET", "/v1/customers/cus_mine")
        client.force_login(user)

        response = client.get(self.url)

        assert response.status_code == 302
        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"

    def test_only_the_signed_in_persons_customer_is_refreshed(
        self, stripe_fake, client, user
    ):
        StripeCustomerFactory(stripe_id="cus_somebody_else")
        client.force_login(user)

        client.get(self.url)

        assert stripe_fake.requests == []

    def test_signing_in_is_required(self, stripe_fake, client, db):
        response = client.get(self.url)

        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))
        assert stripe_fake.requests == []

    def test_coming_back_again_straight_away_does_not_ask_stripe_again(
        self, stripe_fake, client, user
    ):
        """A GET any page can make a browser send must not be a way to spend the rate limit."""
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        stripe_now_holds(
            stripe_fake, "cus_mine", subscription_payload("sub_new", "cus_mine")
        )
        client.force_login(user)
        client.get(self.url)
        asked = len(stripe_fake.requests)

        response = client.get(self.url)

        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"
        assert len(stripe_fake.requests) == asked

    def test_coming_back_again_with_a_session_straight_away_does_not_ask_stripe_again(
        self, stripe_fake, client, user
    ):
        stripe_fake.respond(
            "GET",
            "/v1/checkout/sessions/cs_1",
            checkout_session_payload(
                "cs_1", client_reference_id=f"{user.pk}_forged", customer="cus_new"
            ),
        )
        client.force_login(user)
        client.get(self.url, {"session_id": "cs_1"})
        asked = len(stripe_fake.requests)

        client.get(self.url, {"session_id": "cs_1"})

        assert len(stripe_fake.requests) == asked

    def test_the_pause_is_each_persons_own(self, stripe_fake, client, user):
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        stripe_now_holds(stripe_fake, "cus_mine")
        other = UserFactory()
        StripeCustomerFactory(user=other, stripe_id="cus_other")
        stripe_fake.respond(
            "GET", "/v1/customers/cus_other", customer_payload("cus_other")
        )
        client.force_login(user)
        client.get(self.url)
        client.force_login(other)

        client.get(self.url)

        assert "/v1/customers/cus_other" in stripe_fake.paths()

    def test_coming_back_once_the_pause_is_over_refreshes_again(
        self, stripe_fake, client, user
    ):
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        stripe_now_holds(stripe_fake, "cus_mine")
        client.force_login(user)
        client.get(self.url)
        cache.clear()

        client.get(self.url)

        assert stripe_fake.paths("GET").count("/v1/customers/cus_mine") == 2

    def bought(self, stripe_fake, user, *, reference_user=None, customer="cus_new"):
        reference = Customer.client_reference(reference_user or user)
        stripe_fake.respond(
            "GET",
            "/v1/checkout/sessions/cs_1",
            checkout_session_payload(
                "cs_1", client_reference_id=reference, customer=customer
            ),
        )
        stripe_now_holds(
            stripe_fake, customer, subscription_payload("sub_new", customer)
        )

    def test_a_purchase_is_tied_to_the_person_and_synced_before_the_redirect(
        self, stripe_fake, client, user
    ):
        self.bought(stripe_fake, user)
        client.force_login(user)

        response = client.get(self.url, {"session_id": "cs_1"})

        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"
        customer = Customer.objects.get(user=user)
        assert customer.stripe_id == "cus_new"
        assert list(customer.subscriptions.values_list("stripe_id", flat=True)) == [
            "sub_new"
        ]

    def test_a_person_who_has_a_customer_does_not_ask_stripe_about_the_session(
        self, stripe_fake, client, user
    ):
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        stripe_now_holds(
            stripe_fake, "cus_mine", subscription_payload("sub_new", "cus_mine")
        )
        client.force_login(user)

        client.get(self.url, {"session_id": "cs_1"})

        assert "/v1/checkout/sessions/cs_1" not in stripe_fake.paths()

    def test_a_session_made_for_somebody_else_ties_nothing_to_this_person(
        self, stripe_fake, client, user
    ):
        other = UserFactory()
        self.bought(stripe_fake, user, reference_user=other)
        client.force_login(user)

        response = client.get(self.url, {"session_id": "cs_1"})

        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"
        assert not Customer.objects.filter(user=user).exists()
        assert not Subscription.objects.exists()

    def test_stripe_being_unreachable_for_the_session_still_sends_the_reader_on(
        self, stripe_fake, client, user
    ):
        stripe_fake.become_unreachable("GET", "/v1/checkout/sessions/cs_1")
        client.force_login(user)

        response = client.get(self.url, {"session_id": "cs_1"})

        assert response.url == reverse("payments:stripe-subscription") + "?returned=1"


SESSIONS = "/v1/checkout/sessions"


@pytest.fixture
def on_offer(stripe_fake):
    """Stripe's catalogue holds one price, ``price_pro``, and makes customers as ``cus_made``."""
    pro = {**product_payload("prod_pro", "Pro"), "active": True}
    stripe_fake.respond_with_list("/v1/prices", [price_payload("price_pro", pro)])
    stripe_fake.respond("POST", "/v1/customers", customer_payload("cus_made"))
    return stripe_fake


@pytest.fixture
def checkout_created(on_offer):
    on_offer.respond(
        "POST",
        SESSIONS,
        {
            "id": "cs_1",
            "object": "checkout.session",
            "url": "https://checkout.stripe.com/c/pay/cs_1",
        },
    )
    return on_offer


def messages_of(response):
    return [(m.level_tag, str(m)) for m in get_messages(response.wsgi_request)]


@pytest.mark.django_db
class TestCheckout:
    url = "/account/billing/stripe/checkout/"
    plans = "/plans/"

    def post(self, client, price="price_pro", **extra):
        return client.post(self.url, {"price": price, "return_to": self.plans, **extra})

    def test_a_signed_in_person_is_sent_to_the_session_stripe_made(
        self, checkout_created, client, user
    ):
        client.force_login(user)

        response = self.post(client)

        assert response.status_code == 302
        assert response.url == "https://checkout.stripe.com/c/pay/cs_1"

    def test_stripe_is_asked_for_the_price_with_the_persons_reference_and_both_addresses(
        self, checkout_created, client, user
    ):
        client.force_login(user)

        self.post(client)

        (_, _, params) = checkout_created.requests[-1]
        assert params["line_items[0][price]"] == ["price_pro"]
        assert params["mode"] == ["subscription"]
        assert params["client_reference_id"] == [Customer.client_reference(user)]
        assert params["allow_promotion_codes"] == ["true"]
        assert params["cancel_url"] == ["http://testserver/plans/"]

    def test_the_success_address_returns_through_the_return_view_with_the_session_id_unencoded(
        self, checkout_created, client, user
    ):
        client.force_login(user)

        self.post(client)

        (_, _, params) = checkout_created.requests[-1]
        assert params["success_url"] == [
            "http://testserver"
            + reverse("payments:stripe-billing-return")
            + "?session_id={CHECKOUT_SESSION_ID}"
        ]

    def test_a_person_with_a_customer_buys_as_that_customer(
        self, checkout_created, client, user
    ):
        StripeCustomerFactory(user=user, stripe_id="cus_mine")
        client.force_login(user)

        self.post(client)

        (_, _, params) = checkout_created.requests[-1]
        assert params["customer"] == ["cus_mine"]

    def test_a_person_with_no_customer_has_one_made_and_buys_as_it(
        self, checkout_created, client, user
    ):
        client.force_login(user)

        self.post(client)

        assert Customer.objects.get(user=user).stripe_id == "cus_made"
        (_, _, params) = checkout_created.requests[-1]
        assert params["customer"] == ["cus_made"]
        assert "customer_email" not in params

    def test_a_person_who_is_not_signed_in_is_sent_to_sign_in_and_stripe_is_not_asked(
        self, stripe_fake, client, db
    ):
        response = self.post(client)

        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))
        assert stripe_fake.requests == []

    def test_a_get_is_refused(self, checkout_created, client, user):
        client.force_login(user)

        assert client.get(self.url).status_code == 405
        assert checkout_created.requests == []

    def test_a_post_without_the_csrf_token_is_refused(self, checkout_created, user):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        strict.force_login(user)

        response = strict.post(self.url, {"price": "price_pro"})

        assert response.status_code == 403
        assert checkout_created.requests == []

    def test_a_price_not_on_offer_adds_a_warning_and_creates_nothing(
        self, on_offer, client, user
    ):
        client.force_login(user)

        response = self.post(client, price="price_made_up")

        assert response.url == self.plans
        assert [level for level, _ in messages_of(response)] == ["warning"]
        assert SESSIONS not in on_offer.paths("POST")

    def test_a_missing_price_is_treated_the_same(self, on_offer, client, user):
        client.force_login(user)

        response = client.post(self.url, {"return_to": self.plans})

        assert [level for level, _ in messages_of(response)] == ["warning"]
        assert SESSIONS not in on_offer.paths("POST")

    def test_an_unavailable_catalogue_adds_an_error_not_a_warning(
        self, stripe_fake, client, user
    ):
        stripe_fake.become_unreachable("GET", "/v1/prices")
        client.force_login(user)

        response = self.post(client)

        assert response.url == self.plans
        assert [level for level, _ in messages_of(response)] == ["error"]
        assert SESSIONS not in stripe_fake.paths("POST")

    def test_a_price_the_person_holds_goes_to_the_subscriptions_page(
        self, on_offer, client, user
    ):
        customer = StripeCustomerFactory(user=user)
        StripeSubscriptionFactory(
            customer=customer, price_id="price_pro", status="active"
        )
        client.force_login(user)

        response = self.post(client)

        assert response.url == reverse("payments:stripe-subscription")
        assert SESSIONS not in on_offer.paths("POST")

    def test_a_price_whose_subscription_ended_can_be_bought_again(
        self, checkout_created, client, user
    ):
        customer = StripeCustomerFactory(user=user)
        StripeSubscriptionFactory(
            customer=customer, price_id="price_pro", status="canceled"
        )
        client.force_login(user)

        response = self.post(client)

        assert response.url == "https://checkout.stripe.com/c/pay/cs_1"

    def test_a_stripe_error_adds_an_error_and_returns(
        self, on_offer, client, user, caplog
    ):
        on_offer.respond_with_message_echoing(
            "POST", SESSIONS, "sk_test_not_a_real_key"
        )
        client.force_login(user)

        response = self.post(client)

        assert response.url == self.plans
        assert [level for level, _ in messages_of(response)] == ["error"]
        assert "sk_test_not_a_real_key" not in caplog.text
        assert "AuthenticationError" in caplog.text

    @pytest.mark.parametrize(
        "unsafe", ["https://evil.example/", "//evil.example/", "javascript:alert(1)"]
    )
    def test_an_unsafe_return_to_falls_back_to_the_plans_page(
        self, on_offer, client, user, unsafe
    ):
        client.force_login(user)

        response = client.post(
            self.url, {"price": "price_made_up", "return_to": unsafe}
        )

        assert response.url == self.plans

    def test_a_safe_return_to_on_this_site_is_honoured(self, on_offer, client, user):
        client.force_login(user)

        response = client.post(
            self.url, {"price": "price_made_up", "return_to": "/pricing/?x=1#a"}
        )

        assert response.url == "/pricing/?x=1#a"

    def test_a_customer_stripe_no_longer_has_is_replaced_and_checkout_still_starts(
        self, on_offer, client, user
    ):
        StripeCustomerFactory(user=user, stripe_id="cus_gone")
        on_offer.respond_with_error("GET", "/v1/customers/cus_gone", "resource_missing")
        on_offer.respond_in_turn(
            "POST",
            SESSIONS,
            [
                (
                    {
                        "error": {
                            "type": "invalid_request_error",
                            "code": "resource_missing",
                        }
                    },
                    404,
                ),
                (
                    {
                        "id": "cs_2",
                        "object": "checkout.session",
                        "url": "https://checkout.stripe.com/c/pay/cs_2",
                    },
                    200,
                ),
            ],
        )
        client.force_login(user)

        response = self.post(client)

        assert response.url == "https://checkout.stripe.com/c/pay/cs_2"
        assert Customer.objects.get(user=user).stripe_id == "cus_made"
