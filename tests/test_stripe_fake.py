"""The fake Stripe holds routing and signing logic, so those are checked once here."""

import pytest
import stripe

from mvp_payments.stripe.client import client
from tests.stripe_fake import (
    WEBHOOK_SECRET,
    customer_payload,
    event_payload,
    sign_webhook,
    subscription_payload,
)


class TestFakeStripe:
    def test_the_sdk_parses_a_canned_object(self, stripe_fake):
        stripe_fake.respond("GET", "/v1/customers/cus_1", customer_payload("cus_1"))

        customer = client().v1.customers.retrieve("cus_1")

        assert customer.id == "cus_1"

    def test_a_list_pages_through_to_every_object(self, stripe_fake):
        stripe_fake.respond_with_list(
            "/v1/subscriptions",
            [
                subscription_payload("sub_1", "cus_1"),
                subscription_payload("sub_2", "cus_1"),
            ],
        )

        listed = client().v1.subscriptions.list(params={"customer": "cus_1"})

        assert [s.id for s in listed.auto_paging_iter()] == ["sub_1", "sub_2"]

    def test_a_request_is_recorded_with_its_query(self, stripe_fake):
        stripe_fake.respond_with_list("/v1/subscriptions", [])

        client().v1.subscriptions.list(params={"customer": "cus_1", "status": "all"})

        method, path, params = stripe_fake.requests[0]
        assert (method, path) == ("GET", "/v1/subscriptions")
        assert params == {"customer": ["cus_1"], "status": ["all"]}

    def test_a_canned_error_is_raised_by_the_sdk_with_its_code(self, stripe_fake):
        stripe_fake.respond_with_error(
            "GET", "/v1/customers/cus_gone", "resource_missing"
        )

        with pytest.raises(stripe.InvalidRequestError) as error:
            client().v1.customers.retrieve("cus_gone")

        assert error.value.code == "resource_missing"

    def test_an_unreachable_route_raises_a_connection_error(self, stripe_fake):
        stripe_fake.become_unreachable("GET", "/v1/customers/cus_1")

        with pytest.raises(stripe.APIConnectionError):
            client().v1.customers.retrieve("cus_1")

    def test_a_request_nobody_canned_fails_loudly(self, stripe_fake):
        with pytest.raises(AssertionError, match="/v1/customers/cus_1"):
            client().v1.customers.retrieve("cus_1")


class TestSignWebhook:
    def test_a_signed_payload_passes_the_sdks_verification(self):
        payload = event_payload("customer.deleted", customer_payload("cus_1"))

        event = stripe.Webhook.construct_event(
            payload, sign_webhook(payload), WEBHOOK_SECRET
        )

        assert event.type == "customer.deleted"

    def test_a_payload_signed_with_another_secret_fails_verification(self):
        payload = event_payload("customer.deleted", customer_payload("cus_1"))

        with pytest.raises(stripe.SignatureVerificationError):
            stripe.Webhook.construct_event(
                payload, sign_webhook(payload, secret="whsec_other"), WEBHOOK_SECRET
            )

    def test_an_old_timestamp_fails_verification(self):
        payload = event_payload("customer.deleted", customer_payload("cus_1"))

        with pytest.raises(stripe.SignatureVerificationError):
            stripe.Webhook.construct_event(
                payload, sign_webhook(payload, timestamp=1_000_000_000), WEBHOOK_SECRET
            )
