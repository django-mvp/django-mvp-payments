"""Reversing the pages this package mounts, under the ``payments`` namespace."""

import pytest
from django.urls import NoReverseMatch, resolve, reverse

from mvp_payments.views import PaymentPageView, PlansPageView, SubscriptionPageView


class TestPaymentURLs:
    """Every declared page name resolves; nothing else does."""

    @pytest.mark.parametrize(
        ("name", "view_class"),
        [
            ("drf-stripe-subscription", SubscriptionPageView),
            ("drf-stripe-plans", PlansPageView),
            ("drf-stripe-billing", PaymentPageView),
        ],
    )
    def test_declared_page_name_reverses_to_its_view(self, name, view_class):
        url = reverse(f"payments:{name}")
        assert resolve(url).func.view_class is view_class

    def test_a_name_belonging_to_no_declared_page_does_not_reverse(self):
        with pytest.raises(NoReverseMatch):
            reverse("payments:not-a-declared-page")
