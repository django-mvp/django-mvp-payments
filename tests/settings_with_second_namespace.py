"""``tests.settings``, plus the second namespace's own installed application.

`Contribution.is_available()` only reports a namespace available once its
backend's application is installed (D1), and `mvp_payments/urls.py` builds
`urlpatterns` once, at import, while `MvpPaymentsConfig.ready()` registers
navigation entries once, at startup — both from `INSTALLED_APPS` as it stands
at that point (see `settings_without_backend`). So this is a distinct
settings module a fresh process starts from, not a setting overridden
mid-test.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "tests.second_namespace"]  # noqa: F405
