"""Reversing the pages this package mounts, under the ``payments`` namespace."""

import pytest
from django.urls import NoReverseMatch, resolve, reverse
from mvp_payments.views import PaymentPageView


class TestPaymentURLs:
    """Every declared page name resolves; nothing else does."""

    @pytest.mark.parametrize(
        "name",
        ["drf-stripe-subscription", "drf-stripe-plans", "drf-stripe-billing"],
    )
    def test_declared_page_name_reverses_to_a_page_view(self, name):
        url = reverse(f"payments:{name}")
        assert resolve(url).func.view_class is PaymentPageView

    def test_a_name_belonging_to_no_declared_page_does_not_reverse(self):
        with pytest.raises(NoReverseMatch):
            reverse("payments:not-a-declared-page")
