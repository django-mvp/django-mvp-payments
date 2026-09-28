"""The project's settings with the payment backend removed from ``INSTALLED_APPS``.

Django builds its application registry, the URL configuration and the Account
Center's navigation once, at process start, from ``INSTALLED_APPS``.
Overriding the setting after that point leaves all three exactly as they were
built the first time — a namespace's pages stay mounted and its entries stay
registered no matter what a later test claims about installed applications.

So a fresh process starts from this module, rather than a test overriding the
setting mid-run.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "drf_stripe"]  # noqa: F405
