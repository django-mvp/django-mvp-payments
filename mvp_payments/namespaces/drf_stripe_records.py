"""The drf-stripe-subscription backend's records, as presentation objects.

Reached through ``apps.get_model`` throughout, never imported (Article XII). What counts as
*current* is the backend's own answer, :attr:`StripeUser.current_subscription_items`, never a
status list of ours (ADR 0003).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from django.apps import apps
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import ngettext

from mvp_payments.money import Money


@dataclass(frozen=True)
class PlanFeature:
    """One feature recorded against a plan's product.

    Attributes:
        identifier: The feature's identifier in the backend.
        description: The feature's description, or its identifier where it has none.
    """

    identifier: str
    description: str


@dataclass(frozen=True)
class Plan:
    """One priced item on a current subscription.

    Attributes:
        name: The price's nickname, or its product's name.
        amount: What the item costs per billing interval.
        frequency: The backend's encoding of the billing interval, if it recorded one.
        quantity: How many of the item the subscription holds.
        features: What the item's product grants.
        FREQUENCY_TRANSLATORS: How each interval the backend can report reads in words,
            singular and plural.
    """

    name: str
    amount: Money
    frequency: str | None
    quantity: int
    features: tuple[PlanFeature, ...] = ()

    FREQUENCY_TRANSLATORS: ClassVar[dict[str, Callable[[int], str]]] = {
        "day": lambda n: ngettext("every day", "every %(count)d days", n),
        "week": lambda n: ngettext("every week", "every %(count)d weeks", n),
        "month": lambda n: ngettext("every month", "every %(count)d months", n),
        "year": lambda n: ngettext("every year", "every %(count)d years", n),
    }

    @property
    def frequency_display(self) -> str:
        """The billing frequency in words, or the raw value where it is not recognised.

        drf-stripe-subscription composes ``frequency`` as ``f"{interval}_{interval_count}"``.
        An unrecognised value is shown as itself rather than dropped (Article XV).

        On Python 3.12 and later that f-string formats the backend's ``RecurringInterval`` enum
        member by name, so a synchronised record holds ``RecurringInterval.MONTH_1`` where it
        means ``month_1``. Both spellings are read.
        """
        if not self.frequency:
            return ""
        interval, separator, count_text = self.frequency.rpartition("_")
        if not separator or not count_text.isdigit():
            return self.frequency
        interval = interval.removeprefix("RecurringInterval.").lower()
        translator = self.FREQUENCY_TRANSLATORS.get(interval)
        if translator is None:
            return self.frequency
        count = int(count_text)
        text = translator(count)
        return text if count == 1 else text % {"count": count}


@dataclass(frozen=True)
class CurrentSubscription:
    """One subscription the backend currently grants access for.

    Attributes:
        status: The subscription's status, as the backend recorded it.
        period_start: When the current billing period began, if recorded.
        period_end: When the current billing period ends, if recorded.
        plans: The priced items on the subscription.
    """

    status: str
    period_start: datetime | None
    period_end: datetime | None
    plans: tuple[Plan, ...]


class SubscriptionReader:
    """Reads one person's current subscriptions from the installed backend."""

    @staticmethod
    def for_user(user: AbstractBaseUser) -> tuple[CurrentSubscription, ...]:
        """Read the subscriptions the backend currently grants a person access for.

        Args:
            user: The person whose subscriptions to read.

        Returns:
            The current subscriptions, newest first. Empty for a person the backend holds no
            customer record for.
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
            plans_by_subscription[subscription].append(
                SubscriptionReader.build_plan(item)
            )

        return tuple(
            CurrentSubscription(
                status=subscription.status,
                period_start=subscription.period_start,
                period_end=subscription.period_end,
                plans=tuple(plans_by_subscription[subscription]),
            )
            for subscription in subscriptions
        )

    @staticmethod
    def build_plan(item) -> Plan:
        """Build the ``Plan`` a template reads from one subscription line item.

        Args:
            item: The backend's ``SubscriptionItem``, with its price and product.

        Returns:
            The line item as a plan.
        """
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
