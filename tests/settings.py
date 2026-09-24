"""Django settings for testing django-mvp-payments.

The application configuration — INSTALLED_APPS, MIDDLEWARE, TEMPLATES,
EASY_ICONS, FLEX_MENUS, MVP_CONFIG — lives in ``demo/settings.py`` and is
inherited here rather than restated.

Restating it would mean two descriptions of one application shell, and the
failure that produces is the quiet one: the suite stays green against its own
copy while the project a reader actually opens is broken. Cotton resolves a
component it cannot find to empty output, so that break leaves no error
anywhere.

Only what a test run needs differently is set below.
"""

from demo.settings import *  # noqa: F403

SECRET_KEY = "django-insecure-test-key-for-mvp-payments-tests-only"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# The demo keeps a file on disk so its data survives a restart. A test run
# wants neither the file nor the history.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# A developer's own `demo/.env` holds real sandbox credentials. The suite runs
# as a fresh clone and CI do, on the demo's obviously fake values, so a local
# run never reaches the provider and never depends on whose machine it is.
DEV_ENV: dict[str, str] = {}
DRF_STRIPE = {
    **DRF_STRIPE,  # noqa: F405
    "STRIPE_API_SECRET": "sk_test_not_a_real_key",
}
MVP_PAYMENTS = {
    **MVP_PAYMENTS,  # noqa: F405
    "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_not_a_real_table",
    "DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_not_a_real_key",
}

# The demo's routes, behind a urlconf of the suite's own so a route that exists
# only to exercise a component has somewhere to go.
ROOT_URLCONF = "tests.urls"
