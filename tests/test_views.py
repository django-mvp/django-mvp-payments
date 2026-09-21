"""Rendering a contributed page inside the Account Center layout."""

import json
import os
import re
import subprocess
import sys

import pytest
from django.test import override_settings
from django.urls import reverse

from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.markup import account_center_cards_region

_ACCOUNT_CENTER_WITH_ANOTHER_CARD_PROBE = """
import json

import django

django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)
User.objects.create_user(username="person", password="password")
client = Client()
client.login(username="person", password="password")
response = client.get("/account/")

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
}))
"""


class TestPaymentPage:
    """A signed-in request renders; an anonymous one is sent to sign in."""

    @pytest.mark.parametrize(
        ("url_name", "heading"),
        [
            ("drf-stripe-subscription", "Subscription"),
            ("drf-stripe-plans", "Plans"),
            ("drf-stripe-billing", "Billing"),
        ],
    )
    def test_signed_in_person_sees_the_page_inside_the_account_center(
        self, logged_in_client, url_name, heading
    ):
        response = logged_in_client.get(reverse(f"payments:{url_name}"))
        content = response.content.decode()

        assert response.status_code == 200
        assert re.search(rf"<h1[^>]*>\s*{heading}\s*</h1>", content)
        assert 'aria-label="Account navigation"' in content

    def test_anonymous_visitor_is_sent_to_the_sign_in_page(self, client, db):
        response = client.get(reverse("payments:drf-stripe-subscription"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))


class TestAccountCenterOverview:
    """The overview carries the installed backend's card, and keeps whatever
    django-mvp or another application already put there through
    ``{{ block.super }}`` (FR-006, FR-009).

    Proving the second half needs a second application in the extends chain,
    present from process start — the app-directories template loader order is
    built once, like the URL configuration and the menu (D9) — so this boots
    a fresh process under ``tests.settings_with_another_card`` rather than
    overriding ``INSTALLED_APPS`` mid-test.
    """

    def _open_the_account_center_with_another_card(self) -> dict:
        # sys.executable and a module-level string constant, no untrusted input.
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-c", _ACCOUNT_CENTER_WITH_ANOTHER_CARD_PROBE],
            env={
                **os.environ,
                "DJANGO_SETTINGS_MODULE": "tests.settings_with_another_card",
            },
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout.strip().splitlines()[-1])

    def test_shows_the_installed_backends_card_and_keeps_other_apps_cards(self):
        result = self._open_the_account_center_with_another_card()

        assert result["status_code"] == 200
        cards = account_center_cards_region(result["content"])

        expected_url = reverse("payments:drf-stripe-subscription")
        assert cards.count(f'href="{expected_url}"') == 1
        assert cards.count('data-testid="other-app-card"') == 1


class TestURLsNotMounted:
    """A project that installed the backend but never added the one line
    mounting this package's URL configuration still gets a working Account
    Center, with nothing of this package on it (US-4, FR-009).

    A dead navigation entry is already handled by django-flex-menus, which
    drops a leaf whose URL will not reverse (D3) — the navigation half needs
    no test of its own here beyond confirming it stays true. The card is not
    covered by that: rendering its ``{% url %}`` would raise
    ``NoReverseMatch`` and take the whole page down, which is worse than the
    dead link FR-009 exists to prevent.

    Both guards ask ``reverse()`` live, at render time — ``Contribution.
    is_reachable()`` directly, django-flex-menus' own URL resolution the same
    way — rather than anything built once at process start. That is unlike
    D9's URL-configuration-built-at-import case and D10's template-loader
    case, so this uses ``override_settings(ROOT_URLCONF=...)`` in-process
    rather than a fresh subprocess: confirmed by hand first that Django's own
    ``clear_url_caches()`` (triggered by the ``setting_changed`` signal on a
    ``ROOT_URLCONF`` override) is enough to make every live ``reverse()``
    call in this request see the substituted URL configuration.
    """

    def test_account_center_renders_with_nothing_from_the_unmounted_backend(
        self, logged_in_client
    ):
        with override_settings(ROOT_URLCONF="tests.urls_without_payments"):
            response = logged_in_client.get(reverse("account-center"))

        assert response.status_code == 200
        content = response.content.decode()

        # The page itself still renders, with its own navigation intact — an
        # unmounted backend is not a broken page.
        assert 'aria-label="Account navigation"' in content

        # No navigation entry: covers every one of the backend's pages.
        for page in drf_stripe.pages:
            assert f"<span>{page.label}</span>" not in content

        # No card: its link would need a URL name that cannot reverse here.
        cards = account_center_cards_region(content)
        assert "<a href" not in cards
        for page in drf_stripe.pages:
            assert f">{page.label}<" not in cards
