"""The Stripe app's records about a person, as kinds django-mvp-compliance reads.

A project that uses django-mvp-compliance lists both in ``MVP_COMPLIANCE_PERSONAL_DATA``. A
person's copy of their data then holds their Stripe customer and subscriptions, and deleting
their account deletes the customer at Stripe, which cancels its subscriptions. Nothing else in
this package imports this module, so a project without django-mvp-compliance never needs it.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from mvp_compliance.personal_data import PersonalData

from .models import Customer, Subscription


class StripeCustomer(PersonalData):
    """Who the person is to Stripe: one record at most."""

    heading = _("Your Stripe customer")
    description = _("Who you are to Stripe, which takes this site's payments.")
    model = Customer
    fields = ["stripe_id", "created"]
    single = True

    def get_queryset(self, user):
        """Return the person's customer.

        Args:
            user: The person.

        Returns:
            Their customer, or no rows when they have none.
        """
        return Customer.objects.filter(user=user)

    def erase(self, user):
        """Delete the person's customer at Stripe, which cancels its subscriptions, then here.

        Args:
            user: The person whose account is being deleted.

        Raises:
            stripe.StripeError: When Stripe could not be asked, or refused, so that the
                account's deletion fails as a whole and the person is not left being billed.
        """
        for customer in self.get_queryset(user):
            customer.erase()


class StripeSubscriptions(PersonalData):
    """Every subscription the person has had, as Stripe last reported it."""

    heading = _("Your subscriptions")
    description = _("Each subscription you have had, as Stripe last reported it.")
    model = Subscription
    fields = [
        "stripe_id",
        "product_name",
        "status",
        "amount",
        "currency",
        "interval",
        "interval_count",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
        "ended_at",
    ]

    def get_queryset(self, user):
        """Return the person's subscriptions.

        Args:
            user: The person.

        Returns:
            Every subscription of their customer, latest period first.
        """
        return Subscription.objects.for_user(user)

    def erase(self, user):
        """Delete the person's customer at Stripe, which cancels these subscriptions, then here.

        Args:
            user: The person whose account is being deleted.

        Raises:
            stripe.StripeError: When Stripe could not be asked, or refused, so that the
                account's deletion fails as a whole and the person is not left being billed.
        """
        for customer in Customer.objects.filter(user=user):
            customer.erase()
