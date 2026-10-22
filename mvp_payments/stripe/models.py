"""The local copy of a user's Stripe customer and their subscriptions.

Rows are written only from what Stripe reports (Article XI), never by hand.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.translation import gettext_lazy as _

from .client import client

logger = logging.getLogger(__name__)

#: Keys the HMAC of a checkout reference to this app, so a signature made for another purpose
#: from the same SECRET_KEY can never pass as one.
_REFERENCE_SALT = "mvp_payments.stripe.client_reference"


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

    @classmethod
    def client_reference(cls, user) -> str:
        """Build the reference a page hands to Stripe's pricing table for a signed-in user.

        Stripe carries it through checkout and returns it on the completed session, which is
        how a purchase is tied to a user. It is signed, because the public pricing table could
        otherwise be embedded on another page with someone else's primary key.

        Args:
            user: The signed-in user.

        Returns:
            The user's primary key and an HMAC of it, joined by ``_``. It holds only letters,
            digits and underscores, which is all the pricing table accepts.
        """
        return f"{user.pk}_{cls._signature(user.pk)}"

    @staticmethod
    def _signature(pk) -> str:
        return salted_hmac(_REFERENCE_SALT, str(pk), algorithm="sha256").hexdigest()

    @classmethod
    def from_checkout(cls, session_id: str) -> Customer | None:
        """Tie the customer of a completed checkout to the user who started it.

        Args:
            session_id: Stripe's identifier for the Checkout Session.

        Returns:
            The customer to sync: the one this user already has when it is the same, or a new
            one. ``None`` when the session is not a subscription checkout, carries no
            customer, carries no reference that verifies, names no existing user, or would give
            the user a second customer, or take over one that belongs to another user.

        Raises:
            stripe.StripeError: When Stripe could not be asked, or refused.
        """
        session = client().v1.checkout.sessions.retrieve(session_id)
        if session.mode != "subscription" or not session.client_reference_id:
            return None
        stripe_id = session.customer
        if not stripe_id:
            return None
        pk, _separator, signature = session.client_reference_id.rpartition("_")
        if not constant_time_compare(signature, cls._signature(pk)):
            return None
        user = get_user_model().objects.filter(pk=pk).first()
        if user is None:
            return None
        existing = cls.objects.filter(user=user).first()
        if existing is not None:
            if existing.stripe_id == stripe_id:
                return existing
            logger.error(
                "Checkout %s names Stripe customer %s for user %s, who already has %s.",
                session_id,
                stripe_id,
                user.pk,
                existing.stripe_id,
            )
            return None
        if cls.objects.filter(stripe_id=stripe_id).exists():
            logger.error(
                "Checkout %s names Stripe customer %s for user %s, but it belongs to another user.",
                session_id,
                stripe_id,
                user.pk,
            )
            return None
        return cls.objects.create(user=user, stripe_id=stripe_id)

    def sync(self) -> None:
        """Bring this customer's subscriptions into step with what Stripe holds now.

        The only place subscription rows are written (Article XI). The customer's row is
        locked first, so two webhooks for one customer cannot write an older state over a
        newer one. When Stripe no longer has the customer, the row and its subscriptions are
        deleted. Rows Stripe did not return are deleted.

        Raises:
            stripe.StripeError: When Stripe could not be asked, or refused. Nothing changes.
        """
        with transaction.atomic():
            try:
                customer = Customer.objects.select_for_update().get(pk=self.pk)
            except Customer.DoesNotExist:
                return
            stripe_client = client()
            try:
                remote = stripe_client.v1.customers.retrieve(customer.stripe_id)
            except stripe.InvalidRequestError as error:
                if error.code != "resource_missing":
                    raise
                customer.delete()
                return
            if getattr(remote, "deleted", False):
                customer.delete()
                return

            # Not expanded: Stripe refuses an expansion this deep (data.items.data.price.product).
            listed = stripe_client.v1.subscriptions.list(
                params={"customer": customer.stripe_id, "status": "all", "limit": 100}
            )
            remote_subscriptions = list(listed.auto_paging_iter())
            product_names = {
                product_id: stripe_client.v1.products.retrieve(product_id).name
                for product_id in {
                    subscription["items"]["data"][0]["price"]["product"]
                    for subscription in remote_subscriptions
                }
            }
            for subscription in remote_subscriptions:
                item = subscription["items"]["data"][0]
                price = item["price"]
                Subscription.objects.update_or_create(
                    stripe_id=subscription["id"],
                    defaults={
                        "customer": customer,
                        "status": subscription["status"],
                        "price_id": price["id"],
                        "product_name": product_names[price["product"]],
                        "amount": price["unit_amount"],
                        "currency": price["currency"],
                        "interval": price["recurring"]["interval"],
                        "interval_count": price["recurring"]["interval_count"],
                        "current_period_start": _from_epoch(
                            item["current_period_start"]
                        ),
                        "current_period_end": _from_epoch(item["current_period_end"]),
                        "cancel_at_period_end": subscription["cancel_at_period_end"],
                        "ended_at": _from_epoch(subscription["ended_at"]),
                    },
                )
            customer.subscriptions.exclude(
                stripe_id__in=[
                    subscription["id"] for subscription in remote_subscriptions
                ]
            ).delete()


def _from_epoch(seconds: int | None) -> datetime | None:
    """Convert a Stripe timestamp to an aware datetime.

    Args:
        seconds: Seconds since the epoch, or ``None``.

    Returns:
        The moment in UTC, or ``None`` when Stripe reported none.
    """
    return None if seconds is None else datetime.fromtimestamp(seconds, tz=UTC)


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
