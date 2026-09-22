"""The drf-stripe-subscription backend's records, as presentation objects (D1).

Reached through ``apps.get_model`` throughout, never imported (Article XIII). What counts as
*current* is never decided here: the backend already answers that question everywhere else it is
asked, through :attr:`StripeUser.current_subscription_items`, and naming a status list of our own
would silently go stale the day the backend's own list changes (D1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.apps import apps
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import ngettext

from mvp_payments.money import Money


@dataclass(frozen=True)
class PlanFeature:
    """One feature recorded against a plan's product."""

    identifier: str
    description: str


@dataclass(frozen=True)
class Plan:
    """One priced item on a current subscription."""

    name: str
    amount: Money
    frequency: str | None
    quantity: int
    features: tuple[PlanFeature, ...] = ()

    @property
    def frequency_display(self) -> str:
        """The billing frequency in words, or the raw value where it is not recognised.

        drf-stripe-subscription composes ``frequency`` as ``f"{interval}_{interval_count}"``
        (`research.md`) — a Stripe-specific encoding, so parsing it belongs beside the rest of
        what this module already knows about the backend's vocabulary, and it is shown as itself
        rather than dropped when it is not one this table holds (Article XVI).
        """
        return _describe_frequency(self.frequency)


@dataclass(frozen=True)
class CurrentSubscription:
    """One subscription the backend currently grants access for."""

    status: str
    period_start: datetime | None
    period_end: datetime | None
    plans: tuple[Plan, ...]


class SubscriptionReader:
    """Reads one person's current subscriptions from the installed backend."""

    @staticmethod
    def for_user(user: AbstractBaseUser) -> tuple[CurrentSubscription, ...]:
        """The subscriptions the backend currently grants ``user`` access for, newest first.

        Returns an empty tuple, and raises nothing, for a person the backend holds no customer
        record for at all.
        """
        stripe_user_model = apps.get_model("drf_stripe", "StripeUser")
        try:
            stripe_user = stripe_user_model.objects.get(pk=user.pk)
        except stripe_user_model.DoesNotExist:
            return ()

        items = (
            stripe_user.current_subscription_items.select_related(
                "subscription", "price__product"
            )
            .prefetch_related("price__product__linked_features__feature")
            .order_by("-subscription__period_start")
        )

        subscriptions: list[Any] = []
        plans_by_subscription: dict[Any, list[Plan]] = {}
        for item in items:
            subscription = item.subscription
            if subscription not in plans_by_subscription:
                plans_by_subscription[subscription] = []
                subscriptions.append(subscription)
            plans_by_subscription[subscription].append(_build_plan(item))

        return tuple(
            CurrentSubscription(
                status=subscription.status,
                period_start=subscription.period_start,
                period_end=subscription.period_end,
                plans=tuple(plans_by_subscription[subscription]),
            )
            for subscription in subscriptions
        )


def _build_plan(item) -> Plan:
    price = item.price
    return Plan(
        name=price.nickname or price.product.name,
        amount=Money(minor_units=price.price, currency=price.currency),
        frequency=price.freq,
        quantity=item.quantity,
        features=tuple(
            PlanFeature(
                identifier=product_feature.feature.feature_id,
                description=product_feature.feature.description
                or product_feature.feature.feature_id,
            )
            for product_feature in price.product.linked_features.all()
        ),
    )


_FREQUENCY_TRANSLATORS = {
    "day": lambda n: ngettext("every day", "every %(count)d days", n),
    "week": lambda n: ngettext("every week", "every %(count)d weeks", n),
    "month": lambda n: ngettext("every month", "every %(count)d months", n),
    "year": lambda n: ngettext("every year", "every %(count)d years", n),
}


def _describe_frequency(frequency: str | None) -> str:
    if not frequency:
        return ""
    interval, separator, count_text = frequency.rpartition("_")
    if not separator or not count_text.isdigit():
        return frequency
    translator = _FREQUENCY_TRANSLATORS.get(interval)
    if translator is None:
        return frequency
    count = int(count_text)
    text = translator(count)
    return text if count == 1 else text % {"count": count}
