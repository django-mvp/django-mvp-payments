"""The Stripe app's subscriptions, as presentation objects.

Reached through ``apps.get_model`` throughout, never imported (Article XII). What counts as
*current* is the Stripe app's own answer, ``SubscriptionQuerySet.current``, never a status
list of ours (ADR 0003).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from django.apps import apps
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import ngettext

from mvp_payments.money import Money


@dataclass(frozen=True)
class CurrentSubscription:
    """One subscription the Stripe app counts as the person being subscribed.

    Attributes:
        status: The subscription's status, as Stripe reported it.
        name: The name of the product the subscription is for.
        amount: What the subscription costs per billing interval, or ``None`` when its price
            has no fixed amount.
        interval: The billing interval's unit, as Stripe reports it.
        interval_count: How many intervals pass between bills.
        period_start: When the current billing period began, if recorded.
        period_end: When the current billing period ends, if recorded.
        FREQUENCY_TRANSLATORS: How each interval Stripe can report reads in words,
            singular and plural.
    """

    status: str
    name: str
    amount: Money | None
    interval: str
    interval_count: int
    period_start: datetime | None
    period_end: datetime | None

    FREQUENCY_TRANSLATORS: ClassVar[dict[str, Callable[[int], str]]] = {
        "day": lambda n: ngettext("every day", "every %(count)d days", n),
        "week": lambda n: ngettext("every week", "every %(count)d weeks", n),
        "month": lambda n: ngettext("every month", "every %(count)d months", n),
        "year": lambda n: ngettext("every year", "every %(count)d years", n),
    }

    @staticmethod
    def frequency_words(interval: str, interval_count: int) -> str:
        """Say how often something bills, in words.

        An unrecognised interval is shown as itself rather than dropped (Article XV).

        Args:
            interval: The billing interval's unit, as Stripe reports it.
            interval_count: How many intervals pass between bills.

        Returns:
            Words such as "every month" or "every 3 months" under the current language, the
            raw ``interval_count`` form for an interval not recognised, and an empty string
            for no interval.
        """
        if not interval:
            return ""
        translator = CurrentSubscription.FREQUENCY_TRANSLATORS.get(interval)
        if translator is None:
            return f"{interval}_{interval_count}"
        text = translator(interval_count)
        if interval_count == 1:
            return text
        return text % {"count": interval_count}

    @property
    def frequency_display(self) -> str:
        """The billing frequency in words, or the raw value where it is not recognised."""
        return self.frequency_words(self.interval, self.interval_count)


class SubscriptionReader:
    """Reads one person's current subscriptions from the Stripe app."""

    @staticmethod
    def for_user(user: AbstractBaseUser) -> tuple[CurrentSubscription, ...]:
        """Read the person's current subscriptions, in whatever state Stripe reports.

        Args:
            user: The person whose subscriptions to read, who may not be signed in.

        Returns:
            Every current subscription, newest period first. Empty for a person the app
            holds no customer for.
        """
        subscription_model = apps.get_model("mvp_payments_stripe", "Subscription")
        return tuple(
            CurrentSubscription(
                status=subscription.status,
                name=subscription.product_name,
                amount=None
                if subscription.amount is None
                else Money(
                    minor_units=subscription.amount, currency=subscription.currency
                ),
                interval=subscription.interval,
                interval_count=subscription.interval_count,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
            )
            for subscription in subscription_model.objects.for_user(user).current()
        )
