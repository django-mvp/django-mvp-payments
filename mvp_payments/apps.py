from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MvpPaymentsConfig(AppConfig):
    name = "mvp_payments"
    label = "mvp_payments"
    verbose_name = _("Payments")

    def ready(self) -> None:
        from .namespaces import available_contributions

        for contribution in available_contributions():
            contribution.register()
