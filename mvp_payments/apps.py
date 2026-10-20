"""The application configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MvpPaymentsConfig(AppConfig):
    """Configure the payments application."""

    name = "mvp_payments"
    label = "mvp_payments"
    verbose_name = _("Payments")

    def ready(self) -> None:
        """Register each installed backend's navigation group."""
        from .namespaces import available_contributions

        for contribution in available_contributions():
            contribution.register()
