"""The Stripe app's configuration."""

from django.apps import apps


class TestStripeConfig:
    def test_the_app_is_installed_under_its_own_label(self):
        config = apps.get_app_config("mvp_payments_stripe")

        assert config.name == "mvp_payments.stripe"

    def test_primary_keys_are_big_integers(self):
        config = apps.get_app_config("mvp_payments_stripe")

        assert config.default_auto_field == "django.db.models.BigAutoField"
