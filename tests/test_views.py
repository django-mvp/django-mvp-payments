"""Rendering a contributed page inside the Account Center layout."""

import re

import pytest
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

    def test_anonymous_visitor_is_sent_to_the_sign_in_page(self, client):
        response = client.get(reverse("payments:drf-stripe-subscription"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))
