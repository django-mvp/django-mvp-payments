"""The local copy of a user's Stripe customer and their subscriptions.

Rows are written only from what Stripe reports (Article XI), never by hand.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Customer(models.Model):
    """The Stripe customer tied to one user.

    Attributes:
        user: The user the customer belongs to.
        stripe_id: Stripe's identifier for the customer.
        created: When the customer was first recorded here.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stripe_customer",
        verbose_name=_("user"),
        help_text=_("The user this Stripe customer belongs to."),
    )
    stripe_id = models.CharField(
        _("Stripe ID"),
        max_length=255,
        unique=True,
        help_text=_("Stripe's identifier for the customer, such as cus_123."),
    )
    created = models.DateTimeField(
        _("created"),
        auto_now_add=True,
        help_text=_("When the customer was first recorded here."),
    )

    class Meta:
        verbose_name = _("Stripe customer")
        verbose_name_plural = _("Stripe customers")

    def __str__(self) -> str:
        return self.stripe_id


class SubscriptionQuerySet(models.QuerySet["Subscription"]):
    """Queries over subscriptions."""


class Subscription(models.Model):
    """One Stripe subscription, as Stripe last reported it.

    Attributes:
        customer: The customer the subscription belongs to.
        stripe_id: Stripe's identifier for the subscription.
        status: The status Stripe reported, stored as reported.
        price_id: Stripe's identifier for the price.
        product_name: The name of the product the price belongs to.
        amount: The price in the currency's minor unit, as Stripe reports it.
        currency: The lower-case ISO currency code, as Stripe reports it.
        interval: The billing interval unit: day, week, month or year.
        interval_count: How many intervals pass between bills.
        current_period_start: When the current billing period began.
        current_period_end: When the current billing period ends.
        cancel_at_period_end: Whether the subscription ends when the period does.
        ended_at: When the subscription ended, if it has.
        updated: When the row was last written.
    """

    class Status(models.TextChoices):
        """The statuses Stripe documents. Any other value is still stored."""

        INCOMPLETE = "incomplete", _("Incomplete")
        INCOMPLETE_EXPIRED = "incomplete_expired", _("Incomplete, expired")
        TRIALING = "trialing", _("Trialing")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Past due")
        CANCELED = "canceled", _("Canceled")
        UNPAID = "unpaid", _("Unpaid")
        PAUSED = "paused", _("Paused")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name=_("customer"),
        help_text=_("The Stripe customer this subscription belongs to."),
    )
    stripe_id = models.CharField(
        _("Stripe ID"),
        max_length=255,
        unique=True,
        help_text=_("Stripe's identifier for the subscription, such as sub_123."),
    )
    status = models.CharField(
        _("status"),
        max_length=32,
        choices=Status,
        db_index=True,
        help_text=_("The status Stripe reported, kept exactly as reported."),
    )
    price_id = models.CharField(
        _("price ID"),
        max_length=255,
        help_text=_("Stripe's identifier for the price, such as price_123."),
    )
    product_name = models.CharField(
        _("product name"),
        max_length=255,
        blank=True,
        help_text=_("The name of the product the price belongs to."),
    )
    amount = models.BigIntegerField(
        _("amount"),
        null=True,
        help_text=_(
            "The price in the currency's minor unit, as Stripe reports it. "
            "Empty when the price has no fixed amount."
        ),
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        help_text=_("The lower-case ISO currency code, as Stripe reports it."),
    )
    interval = models.CharField(
        _("billing interval"),
        max_length=16,
        help_text=_("The unit the price is billed in: day, week, month or year."),
    )
    interval_count = models.PositiveIntegerField(
        _("billing interval count"),
        default=1,
        help_text=_("How many billing intervals pass between bills."),
    )
    current_period_start = models.DateTimeField(
        _("current period start"),
        null=True,
        help_text=_("When the current billing period began."),
    )
    current_period_end = models.DateTimeField(
        _("current period end"),
        null=True,
        help_text=_("When the current billing period ends."),
    )
    cancel_at_period_end = models.BooleanField(
        _("cancels at period end"),
        default=False,
        help_text=_("Whether the subscription ends when the current period does."),
    )
    ended_at = models.DateTimeField(
        _("ended at"),
        null=True,
        help_text=_("When the subscription ended. Empty while it has not."),
    )
    updated = models.DateTimeField(
        _("updated"),
        auto_now=True,
        help_text=_("When the row was last written from Stripe."),
    )

    objects = SubscriptionQuerySet.as_manager()

    class Meta:
        ordering = ["-current_period_end"]
        verbose_name = _("Stripe subscription")
        verbose_name_plural = _("Stripe subscriptions")

    def __str__(self) -> str:
        return self.stripe_id
