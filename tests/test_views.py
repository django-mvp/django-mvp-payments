"""Rendering a contributed page inside the Account Center layout."""

import json
import os
import re
import subprocess
import sys

import pytest
from django.urls import reverse

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


def _account_center_cards_region(content: str) -> str:
    """The ``account-center-cards`` div's full content, nested divs and all."""
    marker = content.index('id="account-center-cards"')
    pos = content.rindex("<div", 0, marker)
    depth = 1
    while True:
        next_open = content.find("<div", pos + 1)
        next_close = content.index("</div>", pos + 1)
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open
        else:
            pos = next_close
            depth -= 1
            if depth == 0:
                return content[marker : pos + len("</div>")]


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
        cards = _account_center_cards_region(result["content"])

        expected_url = reverse("payments:drf-stripe-subscription")
        assert cards.count(f'href="{expected_url}"') == 1
        assert cards.count('data-testid="other-app-card"') == 1
