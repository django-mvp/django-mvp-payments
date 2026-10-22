"""System checks for the settings the Stripe app cannot run without."""

from __future__ import annotations

from django.conf import settings
from django.core.checks import CheckMessage, Error, register
from django.utils.translation import gettext as _

REQUIRED = (
    ("STRIPE_SECRET_KEY", "mvp_payments_stripe.E001"),
    ("STRIPE_WEBHOOK_SECRET", "mvp_payments_stripe.E002"),
)


@register()
def check_settings(app_configs, **kwargs) -> list[CheckMessage]:
    """Report each required ``MVP_PAYMENTS`` setting that is missing or empty.

    Args:
        app_configs: The app configs being checked, ignored.
        **kwargs: The rest of the check framework's arguments.

    Returns:
        One error per missing setting. A message names the setting, never a value.
    """
    configured = getattr(settings, "MVP_PAYMENTS", {})
    return [
        Error(
            _("MVP_PAYMENTS['%(name)s'] is not set.") % {"name": name},
            hint=_("Set it in the project's settings, from runtime configuration."),
            id=check_id,
        )
        for name, check_id in REQUIRED
        if not configured.get(name)
    ]
