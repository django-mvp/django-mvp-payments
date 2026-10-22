"""Read-only admin for the records the app keeps (Article XI).

Nothing here can be added, changed or deleted by hand: a record changes only when Stripe
reports a change.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from mvp_payments.money import Money

from .models import Customer, Subscription

user_model = get_user_model()
USER_SEARCH_FIELDS = (
    f"user__{user_model.USERNAME_FIELD}",
    f"user__{user_model.get_email_field_name()}",
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Shows a record and offers no way to alter it."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Refuse adding, to everyone.

        Args:
            request: The request being served.

        Returns:
            Always ``False``.
        """
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Refuse changing, to everyone.

        Args:
            request: The request being served.
            obj: The record, if one is open.

        Returns:
            Always ``False``.
        """
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Refuse deleting from this app's own pages, and defer to Django elsewhere.

        Django drops the bulk delete action from a list on which this returns ``False``.

        Django asks every registered model's admin whether it may delete a record that a
        deletion cascades to, so refusing everywhere would also stop a user with a Stripe
        customer from being deleted in the user admin.

        Args:
            request: The request being served.
            obj: The record, if one is open.

        Returns:
            ``False`` on this app's own pages, otherwise Django's answer.
        """
        match = request.resolver_match
        url_name = match.url_name if match is not None else None
        if url_name and url_name.startswith(f"{self.opts.app_label}_"):
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Customer)
class CustomerAdmin(ReadOnlyAdmin):
    """Who each user's Stripe customer is."""

    list_display = ("user", "stripe_id", "created")
    list_select_related = ("user",)
    search_fields = (*USER_SEARCH_FIELDS, "stripe_id")


@admin.register(Subscription)
class SubscriptionAdmin(ReadOnlyAdmin):
    """Each subscription with its status, price and period."""

    list_display = (
        "stripe_id",
        "user",
        "status_label",
        "product_name",
        "current_period_end",
    )
    list_filter = ("status",)
    list_select_related = ("customer__user",)
    search_fields = (
        *(f"customer__{field}" for field in USER_SEARCH_FIELDS),
        "stripe_id",
        "customer__stripe_id",
    )
    fields = (
        "user",
        "customer",
        "stripe_id",
        "status_label",
        "product_name",
        "price_id",
        "price",
        "interval",
        "interval_count",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
        "ended_at",
        "updated",
    )
    readonly_fields = ("user", "status_label", "price")

    @admin.display(
        description=_("user"), ordering=f"customer__user__{user_model.USERNAME_FIELD}"
    )
    def user(self, obj: Subscription):
        """Show the user the subscription's customer belongs to.

        Args:
            obj: The subscription.

        Returns:
            The user.
        """
        return obj.customer.user

    @admin.display(description=_("status"), ordering="status")
    def status_label(self, obj: Subscription) -> str:
        """Show the status, as stored when the app does not know it.

        A choices field would show a placeholder for a status Stripe adds later.

        Args:
            obj: The subscription.

        Returns:
            The status's label, or the status itself when it has none.
        """
        return obj.get_status_display()

    @admin.display(description=_("price"))
    def price(self, obj: Subscription) -> str:
        """Show the amount in its own currency, or nothing when Stripe reported no amount.

        Args:
            obj: The subscription.

        Returns:
            The formatted amount with its currency code, or an empty string.
        """
        if obj.amount is None:
            return ""
        return str(Money(obj.amount, obj.currency))
