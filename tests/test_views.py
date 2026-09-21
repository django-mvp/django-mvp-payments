"""Rendering a contributed page inside the Account Center layout."""

import re

import pytest
from django.test import override_settings
from django.urls import reverse


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
    ``{{ block.super }}`` (FR-006, FR-009)."""

    def test_shows_the_installed_backends_card_and_keeps_other_apps_cards(
        self, logged_in_client, settings
    ):
        apps_with_another_card = list(settings.INSTALLED_APPS)
        apps_with_another_card.insert(
            apps_with_another_card.index("mvp"), "tests.other_app"
        )

        with override_settings(INSTALLED_APPS=apps_with_another_card):
            response = logged_in_client.get(reverse("account-center"))
        content = response.content.decode()

        assert response.status_code == 200
        start = content.index('id="account-center-cards"')
        cards = content[start : content.index("</div>", start)]

        expected_url = reverse("payments:drf-stripe-subscription")
        assert cards.count(f'href="{expected_url}"') == 1
        assert cards.count('data-testid="other-app-card"') == 1
