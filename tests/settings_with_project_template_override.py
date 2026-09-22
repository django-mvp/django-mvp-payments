"""``tests.settings``, plus a project application supplying its own subscription-page template.

FR-011 requires that overriding the subscription page's template needs no view, no context
processor and no query of the project's own. Proving it needs the project's copy of
``mvp_payments/drf_stripe/subscription.html`` to be found first, which the app-directories
template loader decides from ``INSTALLED_APPS`` order at process start (D4,
001-pages-arrive-on-install) — the same reason ``settings_with_another_card`` boots a fresh
process rather than reordering ``INSTALLED_APPS`` mid-test.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = ["tests.project_app", *INSTALLED_APPS]  # noqa: F405
