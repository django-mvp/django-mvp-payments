"""The Stripe app's configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StripeConfig(AppConfig):
    """Configure the app that keeps each user's Stripe subscription in the database."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mvp_payments.stripe"
    label = "mvp_payments_stripe"
    verbose_name = _("Stripe")

    def ready(self) -> None:
        """Register the system checks."""
        from . import checks  # noqa: F401
