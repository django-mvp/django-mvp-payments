"""Reversing the pages this package mounts, under the ``payments`` namespace."""

import pytest
from django.urls import NoReverseMatch, resolve, reverse

from mvp_payments.views import PlansPageView, SubscriptionPageView


class TestPaymentURLs:
    """Every declared page name resolves; nothing else does."""

    @pytest.mark.parametrize(
        ("name", "view_class"),
        [
            ("drf-stripe-subscription", SubscriptionPageView),
            ("drf-stripe-plans", PlansPageView),
        ],
    )
    def test_declared_page_name_reverses_to_its_view(self, name, view_class):
        url = reverse(f"payments:{name}")
        assert resolve(url).func.view_class is view_class

    def test_a_page_kept_out_of_the_navigation_still_reverses(self):
        """The plans page is reached from the subscription page, not from the menu.

        Leaving the navigation is not the same as leaving the site, so the
        address has to keep working for anything that links to it.
        """
        assert reverse("payments:drf-stripe-plans")

    def test_a_name_belonging_to_no_declared_page_does_not_reverse(self):
        with pytest.raises(NoReverseMatch):
            reverse("payments:not-a-declared-page")

    def test_the_retired_billing_page_no_longer_reverses(self):
        """Its content is a control on the subscription page now, not a page."""
        with pytest.raises(NoReverseMatch):
            reverse("payments:drf-stripe-billing")
