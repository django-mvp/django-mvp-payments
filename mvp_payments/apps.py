from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MvpPaymentsConfig(AppConfig):
    name = "mvp_payments"
    label = "mvp_payments"
    verbose_name = _("Payments")
