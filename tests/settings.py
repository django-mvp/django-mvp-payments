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

# The demo's routes, behind a urlconf of the suite's own so a route that exists
# only to exercise a component has somewhere to go.
ROOT_URLCONF = "tests.urls"
