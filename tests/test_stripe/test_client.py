"""The Stripe client the app builds from the project's settings."""

import json

import pytest
import stripe
from django.core.exceptions import ImproperlyConfigured

from mvp_payments.stripe import client as client_module
from mvp_payments.stripe.client import API_VERSION, client


class RecordingHTTPClient(stripe.HTTPClient):
    """Answers every request with a bare customer and remembers the request headers."""

    name = "recording"

    def __init__(self):
        super().__init__()
        self.headers = []

    def request(self, method, url, headers, post_data=None, *, _usage=None):
        self.headers.append(dict(headers))
        return json.dumps({"id": "cus_1", "object": "customer"}), 200, {}


@pytest.fixture
def recorder(monkeypatch):
    http_client = RecordingHTTPClient()
    monkeypatch.setattr(client_module, "_http_client", http_client)
    return http_client


class TestClient:
    def test_the_configured_secret_key_authorises_the_request(self, settings, recorder):
        settings.MVP_PAYMENTS = {"STRIPE_SECRET_KEY": "sk_test_configured"}

        client().v1.customers.retrieve("cus_1")

        assert recorder.headers[0]["Authorization"] == "Bearer sk_test_configured"

    def test_every_request_names_the_api_version_the_app_is_written_against(
        self, settings, recorder
    ):
        settings.MVP_PAYMENTS = {"STRIPE_SECRET_KEY": "sk_test_configured"}

        client().v1.customers.retrieve("cus_1")

        assert recorder.headers[0]["Stripe-Version"] == API_VERSION

    def test_the_sdks_global_configuration_is_not_used(self, settings, recorder):
        settings.MVP_PAYMENTS = {"STRIPE_SECRET_KEY": "sk_test_configured"}
        stripe.api_key = "sk_test_global"

        try:
            client().v1.customers.retrieve("cus_1")
        finally:
            stripe.api_key = None

        assert recorder.headers[0]["Authorization"] == "Bearer sk_test_configured"

    @pytest.mark.parametrize("mvp_payments", [{}, {"STRIPE_SECRET_KEY": ""}])
    def test_a_missing_secret_key_is_a_configuration_error(
        self, settings, mvp_payments
    ):
        settings.MVP_PAYMENTS = mvp_payments

        with pytest.raises(ImproperlyConfigured) as error:
            client()

        assert "STRIPE_SECRET_KEY" in str(error.value)
