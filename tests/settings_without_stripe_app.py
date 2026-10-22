"""The project's settings with the Stripe app removed from ``INSTALLED_APPS``.

The URL configuration is built once, at process start, from ``INSTALLED_APPS``, so a fresh
process starts from this module rather than a test overriding the setting mid-run.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "mvp_payments.stripe"]  # noqa: F405
