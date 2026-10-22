"""Reversing the pages this package mounts, under the ``payments`` namespace."""

import pytest
from django.urls import NoReverseMatch, resolve, reverse

from mvp_payments.views import PlansPageView, SubscriptionPageView


class TestPaymentURLs:
    @pytest.mark.parametrize(
        ("name", "view_class"),
        [("stripe-subscription", SubscriptionPageView)],
    )
    def test_declared_page_name_reverses_to_its_view(self, name, view_class):
        url = reverse(f"payments:{name}")
        assert resolve(url).func.view_class is view_class

    def test_the_plans_page_is_not_one_of_the_account_centers_pages(self):
        with pytest.raises(NoReverseMatch):
            reverse("payments:stripe-plans")

    def test_the_plans_page_reverses_under_its_own_namespace(self):
        url = reverse("payments_plans:stripe-plans")
        assert resolve(url).func.view_class is PlansPageView

    def test_a_name_belonging_to_no_declared_page_does_not_reverse(self):
        with pytest.raises(NoReverseMatch):
            reverse("payments:not-a-declared-page")

    def test_the_retired_billing_page_no_longer_reverses(self):
        with pytest.raises(NoReverseMatch):
            reverse("payments:stripe-billing")
