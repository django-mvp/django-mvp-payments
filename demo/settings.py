"""Settings for the demo project.

Demonstration target, never deployed. It runs on the development server so the
components can be looked at in a browser while they are being built.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _dev_env() -> dict[str, str]:
    """Read `demo/.env`, which is untracked and never committed.

    It holds the provider sandbox credentials that make the provider's own
    hosted pages reachable from this demo. Without the file the demo still runs,
    on values that are obviously not real. `demo/.env.example` lists every value
    and where in the provider's dashboard it comes from.

    Returns:
        The file's values, empty when the file does not exist.
    """
    values: dict[str, str] = {}
    env_file = BASE_DIR / "demo" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator and not key.lstrip().startswith("#"):
                values[key.strip()] = value.strip().strip("\"'")
    values.update(
        {
            key: os.environ[key]
            for key in (
                "STRIPE_TEST_SECRET_KEY",
                "STRIPE_TEST_PUBLISHABLE_KEY",
                "STRIPE_TEST_PRICING_TABLE_ID",
                "DEMO_BASE_URL",
            )
            if key in os.environ
        }
    )
    return values


DEV_ENV = _dev_env()

SECRET_KEY = "django-insecure-demo-project-only"

DEBUG = True

# The development server is reached over the network by hostname, not only at
# localhost. DEBUG auto-allows localhost and nothing else, so a bare list here
# answers any other hostname with 400 Bad Request.
ALLOWED_HOSTS = ["*"]

# The development server speaks plain HTTP. A cookie marked Secure is discarded
# by the browser, which leaves GET pages rendering perfectly while every form
# post comes back 403.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Order matters: the first copy of a template name wins. `demo` supplies `base.html`,
# `mvp_payments` overrides and extends `mvp/account/overview.html`, and `mvp`
# overrides `crispy_tailwind`'s help-text template.
INSTALLED_APPS = [
    "demo",
    "mvp_payments",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "mvp",
    "easy_icons",
    "crispy_forms",
    "crispy_tailwind",
    "flex_menu",
    "django_cotton",
    "rest_framework",
    "drf_stripe",
]

# Without a secret in `demo/.env` the handoff reports the portal unreachable, as a
# misconfigured project would. The return address replaces the backend's default of a
# frontend on port 3000, and is overridable because the server's hostname varies.
DRF_STRIPE = {
    "STRIPE_API_SECRET": DEV_ENV.get(
        "STRIPE_TEST_SECRET_KEY", "sk_test_not_a_real_key"
    ),
    "STRIPE_WEBHOOK_SECRET": "whsec_not_a_real_secret",
    "FRONT_END_BASE_URL": DEV_ENV.get("DEMO_BASE_URL", "http://localhost:8020"),
}

# The portal endpoints are this project's own, not the backend's, which raises for anybody
# who has used it before (demo/views.py). The pricing table values come from `demo/.env`,
# or are obviously fake, and the provider's embed then reports that it could not load.
MVP_PAYMENTS = {
    "DRF_STRIPE_BILLING_PORTAL": "/api/billing-portal/",
    "DRF_STRIPE_PLAN_SWITCH": "/api/plan-switch/",
    "DRF_STRIPE_PRICING_TABLE_ID": DEV_ENV.get(
        "STRIPE_TEST_PRICING_TABLE_ID", "prctbl_not_a_real_table"
    ),
    "DRF_STRIPE_PUBLISHABLE_KEY": DEV_ENV.get(
        "STRIPE_TEST_PUBLISHABLE_KEY", "pk_test_not_a_real_key"
    ),
}

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # The shell puts the site's name in every page title and in the navbar,
    # reading it from request.site. This middleware is what puts it there;
    # without it the name renders empty and nothing raises.
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "mvp.context_processors.mvp_config",
            ],
        },
    },
]

WSGI_APPLICATION = "demo.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "demo.sqlite3",
    }
}

CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]
CRISPY_TEMPLATE_PACK = "tailwind"

# django-mvp's development sign-in pages, registered by the Account Center's URLconf.
# The shell draws its sign-out control only when `account_logout` resolves.
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "account-center"

# Neither key is checked at startup: a missing one fails when a page first renders a menu.
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}

# Left unset, the first icon on the page raises.
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
        "icons": {
            "payments": "bi bi-credit-card",
            "plan": "bi bi-collection",
            "subscription": "bi bi-arrow-repeat",
        },
    },
}

# Deep-merged over django-mvp's defaults, so only the differences appear here.
MVP_CONFIG = {
    "layout": {
        "sidebar": {
            "title": "django-mvp-payments",
            # Narrow to an icon rail rather than sliding away, so a pricing
            # page can be given the full width without losing its navigation.
            "collapse": "icons",
        },
    },
    "theme": {
        # Several themes, so it can be seen that the components follow the site's theme.
        "choices": ["light", "dark", "corporate", "dracula"],
    },
}

STATIC_URL = "/static/"

USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "en-us"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
