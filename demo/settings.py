"""Settings for the demo project.

Demonstration target, never deployed. It runs on the development server so the
components can be looked at in a browser while they are being built.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _dev_env() -> dict[str, str]:
    """Values from `demo/.env`, which is untracked and never committed.

    It holds the provider sandbox credentials that make the provider's own
    hosted pages reachable from this demo, so the handoff to them can be
    exercised rather than described. Without the file the demo still runs, on
    values that are obviously not real, which is what a fresh clone and the
    test suite get. Nothing here reaches a project that installs the package:
    a demo project is a demonstration target and ships to nobody.
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
            for key in ("STRIPE_TEST_SECRET_KEY", "DEMO_BASE_URL")
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

# Django's app template loader takes the first copy of a template name it finds,
# so this project's own apps come above `mvp` — that is what lets the demo
# supply `base.html`, the name django-mvp's packaged page templates extend.
# `mvp` in turn comes above `crispy_tailwind`, whose help-text template it
# overrides.
#
# `mvp_payments` above `mvp` is load-bearing for the same reason: it ships its
# own copy of `mvp/account/overview.html` and extends the name from inside it,
# which only resolves when this application is found first.
#
# `drf_stripe` is here because this demo demonstrates a payment backend's pages
# arriving, which needs the backend installed. It is a development dependency of
# this repository and reaches no project that installs the package.
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

# The backend reads every one of its settings through defaults, so nothing here
# is required to make it start. The secret comes from `demo/.env` where that
# file exists, which is what lets the subscription page's handoff actually
# arrive at the provider's hosted portal instead of failing; without it the
# value is obviously not a real key and the handoff reports that it could not
# be reached, which is the same thing a misconfigured project would see.
#
# The return address is this site rather than the backend's default of a
# frontend on port 3000, and it is overridable because the development server
# is reached by hostname on some machines and by localhost on others. The
# provider sends a reader back to it, so a wrong value strands them.
DRF_STRIPE = {
    "STRIPE_API_SECRET": DEV_ENV.get(
        "STRIPE_TEST_SECRET_KEY", "sk_test_not_a_real_key"
    ),
    "STRIPE_WEBHOOK_SECRET": "whsec_not_a_real_secret",
    "FRONT_END_BASE_URL": DEV_ENV.get("DEMO_BASE_URL", "http://localhost:8020"),
}

# Where this project mounted the endpoint the subscription page hands a reader
# to (demo/urls.py). Neither candidate carries a route name, so the page has to
# be told where it is rather than assuming (D3, FR-006).
#
# This project's own rather than the backend's, because the backend's raises
# for anybody who has used it before — demo/views.py has the whole of it. Which
# of the two a project points at is exactly the decision this setting exists to
# let a project make.
#
# The pricing table id and publishable key are this demonstration's own,
# obviously fake values — not a real table, not a real account — for the
# Plans page to mount the provider's pricing table with (T009).
MVP_PAYMENTS = {
    "DRF_STRIPE_BILLING_PORTAL": "/api/billing-portal/",
    "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_not_a_real_table",
    "DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_not_a_real_key",
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

# Where a view that requires a signed-in person sends everyone else, and where
# signing in returns to. Django's default for the first is /accounts/login/,
# which is where demo/urls.py mounts it, but stating it keeps the demo honest
# about the contract a host project is expected to have.
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "account-center"
LOGOUT_REDIRECT_URL = "home"

# Which class draws the sidebar tree declared in demo/menus.py, and which draws
# the dock shown below the sidebar breakpoint. Neither key is checked at
# startup: a missing one fails when a page first renders a menu.
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}

# Icons are referenced by name. django-mvp's pack covers the names the shell
# uses for itself; anything this project names goes on top of it. Leave the
# setting unset and the first icon on the page raises.
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
        # A component renders semantic daisyUI classes rather than literal
        # colours, so a pricing page follows the site when the theme changes.
        # Offering several here is how that claim gets looked at.
        "choices": ["light", "dark", "corporate", "dracula"],
    },
}

STATIC_URL = "/static/"

USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "en-us"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
