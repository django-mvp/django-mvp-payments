"""System checks for the settings the Stripe app cannot run without, or run well without."""

from __future__ import annotations

from django.conf import settings
from django.core import checks
from django.core.checks import CheckMessage, Error, register
from django.utils.translation import gettext as _

REQUIRED = (
    ("STRIPE_SECRET_KEY", "mvp_payments_stripe.E001"),
    ("STRIPE_WEBHOOK_SECRET", "mvp_payments_stripe.E002"),
)

DUMMY_CACHE = "django.core.cache.backends.dummy.DummyCache"


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


@register()
def check_cache(app_configs, **kwargs) -> list[CheckMessage]:
    """Warn when the default cache keeps nothing, so every plans page view asks Stripe.

    The catalogue, and the minute Stripe is remembered as unavailable, live in the default
    cache. Without one, each visitor to the plans page is a request to Stripe, and during an
    outage each holds a worker until the request times out.

    Args:
        app_configs: The app configs being checked, ignored.
        **kwargs: The rest of the check framework's arguments.

    Returns:
        One warning when the default cache is Django's dummy cache.
    """
    if settings.CACHES.get("default", {}).get("BACKEND") != DUMMY_CACHE:
        return []
    return [
        checks.Warning(
            _(
                "CACHES['default'] is the dummy cache, so the Stripe catalogue is never kept."
            ),
            hint=_(
                "Use a cache that keeps entries, so the plans page does not ask Stripe on "
                "every view."
            ),
            id="mvp_payments_stripe.W001",
        )
    ]
