"""What the plans components need to draw the plans for one reader.

The prices come from the Stripe app's catalogue, reached through the app registry because
the interface never imports a provider app (Article XI).
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.apps import apps
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.translation import gettext

from mvp_payments.contributions import APP_NAMESPACE
from mvp_payments.namespaces.stripe_records import CurrentSubscription


class PlanChoices:
    """The prices on offer, and how this reader can buy each one.

    Attributes:
        INTERVAL_DAYS: How long one interval of each unit lasts, to put billing
            frequencies in order.
    """

    INTERVAL_DAYS: ClassVar[dict[str, int]] = {
        "day": 1,
        "week": 7,
        "month": 30,
        "year": 365,
    }

    @staticmethod
    def interval_key(price: dict[str, Any]) -> str:
        """Name a price's billing frequency with one string.

        Args:
            price: A price as the catalogue returns it.

        Returns:
            The unit and the count, such as ``month_1``.
        """
        recurring = price["recurring"]
        return f"{recurring['interval']}_{recurring['interval_count']}"

    @staticmethod
    def interval_label(price: dict[str, Any]) -> str:
        """Name a price's billing frequency as a switch label.

        Args:
            price: A price as the catalogue returns it.

        Returns:
            Monthly, Yearly or similar for a count of one, the frequency in words
            otherwise, and the raw interval where it is not recognised.
        """
        recurring = price["recurring"]
        if recurring["interval_count"] == 1:
            labels = {
                "day": gettext("Daily"),
                "week": gettext("Weekly"),
                "month": gettext("Monthly"),
                "year": gettext("Yearly"),
            }
            return str(labels.get(recurring["interval"], recurring["interval"]))
        return CurrentSubscription.frequency_words(
            recurring["interval"], recurring["interval_count"]
        ).capitalize()

    @classmethod
    def intervals(cls, prices: list[dict[str, Any]]) -> list[dict[str, str]]:
        """List the distinct billing frequencies on offer, shortest first.

        Args:
            prices: The prices on offer.

        Returns:
            One ``key`` and ``label`` for each frequency.
        """
        shortest_first = sorted(
            prices,
            key=lambda price: (
                cls.INTERVAL_DAYS.get(price["recurring"]["interval"], 0)
                * price["recurring"]["interval_count"]
            ),
        )
        distinct = {cls.interval_key(price): price for price in shortest_first}
        return [
            {"key": key, "label": cls.interval_label(price)}
            for key, price in distinct.items()
        ]

    @classmethod
    def for_request(cls, request: HttpRequest) -> dict[str, Any]:
        """Gather everything the plans components read, for the person making this request.

        Args:
            request: The request the plans are drawn for.

        Returns:
            ``prices`` (``None`` when the catalogue cannot be read, including when the
            Stripe app is not installed), ``intervals`` and
            ``first_interval`` for the frequency switch, ``held`` (the price ids the
            signed-in person currently subscribes to), ``ready`` (the price picked before
            signing in), ``signed_in`` and the addresses ``login_url``, ``checkout_url``
            and ``subscriptions_url``, with ``return_to``, the page the plans are on.
        """
        stripe_app: Any = (
            apps.get_app_config("mvp_payments_stripe")
            if apps.is_installed("mvp_payments.stripe")
            else None
        )
        prices = stripe_app.catalogue.prices() if stripe_app else None
        intervals = cls.intervals(prices or [])
        ready = request.GET.get("plan", "")
        first_interval = intervals[0]["key"] if intervals else ""
        for price in prices or []:
            if price["id"] == ready:
                first_interval = cls.interval_key(price)
        held: list[str] = []
        user = request.user
        if stripe_app and user.is_authenticated:
            subscription_model = apps.get_model("mvp_payments_stripe", "Subscription")
            held = list(
                subscription_model.objects.for_user(user)
                .current()
                .values_list("price_id", flat=True)
            )
        return {
            "prices": prices,
            "intervals": intervals,
            "first_interval": first_interval,
            "held": held,
            "ready": ready,
            "signed_in": user.is_authenticated,
            "login_url": resolve_url(settings.LOGIN_URL),
            "checkout_url": (
                reverse(f"{APP_NAMESPACE}:stripe-checkout") if stripe_app else ""
            ),
            "subscriptions_url": (
                reverse(f"{APP_NAMESPACE}:stripe-subscription") if stripe_app else ""
            ),
            "return_to": request.path,
        }
