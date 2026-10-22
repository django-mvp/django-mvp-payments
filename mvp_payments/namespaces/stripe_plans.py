"""What the plans components need to draw the plans for one reader (FS-005 sketch).

SKETCH: the catalogue comes from ``SketchCatalogue`` until the Stripe app reads and caches
Stripe's (FR-014). The rest is what the screens need from the code, whoever builds it.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.translation import gettext

from mvp_payments.contributions import APP_NAMESPACE
from mvp_payments.namespaces.stripe_catalogue import SketchCatalogue
from mvp_payments.namespaces.stripe_records import CurrentSubscription


class PlanChoices:
    """The prices on offer, and how this reader can buy each one."""

    @staticmethod
    def interval_key(price: dict[str, Any]) -> str:
        """One string per billing frequency, such as ``month_1``."""
        recurring = price["recurring"]
        return f"{recurring['interval']}_{recurring['interval_count']}"

    @staticmethod
    def interval_label(price: dict[str, Any]) -> str:
        """A billing frequency as a switch label: Monthly, Yearly, Every 3 months."""
        recurring = price["recurring"]
        if recurring["interval_count"] == 1:
            labels = {
                "day": gettext("Daily"),
                "week": gettext("Weekly"),
                "month": gettext("Monthly"),
                "year": gettext("Yearly"),
            }
            return str(labels.get(recurring["interval"], recurring["interval"]))
        return CurrentSubscription(
            status="",
            name="",
            amount=None,
            interval=recurring["interval"],
            interval_count=recurring["interval_count"],
            period_start=None,
            period_end=None,
        ).frequency_display.capitalize()

    @classmethod
    def for_request(cls, request: HttpRequest) -> dict[str, Any]:
        """Everything the plans components read, for the person making this request."""
        variant = request.GET.get("sketch", "")
        prices = SketchCatalogue.prices(variant)
        intervals: list[dict[str, str]] = []
        for price in prices or []:
            key = cls.interval_key(price)
            if key not in [i["key"] for i in intervals]:
                intervals.append({"key": key, "label": cls.interval_label(price)})
        held: list[str] = []
        user = request.user
        if user.is_authenticated:
            subscription_model = apps.get_model("mvp_payments_stripe", "Subscription")
            held = list(
                subscription_model.objects.for_user(user)
                .current()
                .values_list("price_id", flat=True)
            )
        ready = request.GET.get("plan", "")
        first_interval = intervals[0]["key"] if intervals else ""
        for price in prices or []:
            if price["id"] == ready:
                first_interval = cls.interval_key(price)
        return {
            "prices": prices,
            "intervals": intervals,
            "first_interval": first_interval,
            "held": held,
            "ready": ready,
            "signed_in": user.is_authenticated,
            "login_url": resolve_url(settings.LOGIN_URL),
            "checkout_url": reverse(f"{APP_NAMESPACE}:stripe-checkout"),
            "subscriptions_url": reverse(f"{APP_NAMESPACE}:stripe-subscription"),
            "return_to": request.path,
        }
