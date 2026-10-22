"""The page view every contribution's pages are built from.

One view class rather than one per page: each :class:`~mvp_payments.contributions.Page`
becomes an instance of this view, built through ``as_view(page=...)``, taking its
template and heading from the page it was built for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.functional import Promise
from mvp.views import MVPTemplateView

from .namespaces.stripe_records import SubscriptionReader

if TYPE_CHECKING:
    from .contributions import Contribution, Page


class PaymentPageView(AccessMixin, MVPTemplateView):
    """One page a namespace contributes, following ``AccountCenterView``'s shape.

    A visitor who is not signed in is sent to sign in, unless the page sets
    ``login_required=False``.

    Never used directly, only built once per declared ``Page`` through ``as_view()``.

    Attributes:
        page: The page this view renders, set through ``as_view(page=...)``.
        contribution: The contribution the page belongs to, set through
            ``as_view(contribution=...)``. It is how a page addresses a sibling that
            is not in the navigation.
    """

    page: Page | None = None
    contribution: Contribution | None = None

    def dispatch(self, request, *args, **kwargs):
        """Send a visitor who is not signed in to sign in, unless the page is open to all."""
        if self.get_page().login_required and not request.user.is_authenticated:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_page(self) -> Page:
        """Return the page this view was built for.

        Returns:
            The page passed to ``as_view()``.

        Raises:
            ImproperlyConfigured: The view was built without a page.
        """
        if self.page is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} requires `page` to be set, via as_view(page=...)."
            )
        return self.page

    def get_contribution(self) -> Contribution:
        """Return the contribution this view's page belongs to.

        Returns:
            The contribution passed to ``as_view()``.

        Raises:
            ImproperlyConfigured: The view was built without a contribution.
        """
        if self.contribution is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} requires `contribution` to be set, "
                "via as_view(contribution=...)."
            )
        return self.contribution

    def get_template_names(self) -> list[str]:
        """Render the page's own template."""
        return [self.get_page().template_name]

    def get_page_title(self) -> str | Promise:
        """Title the page with its label."""
        return self.get_page().label


class SubscriptionPageView(PaymentPageView):
    """The Stripe namespace's user subscriptions page: what the signed-in person is on.

    Adds to the context:

    - ``subscriptions``: every one of this person's current subscriptions, read at render time
      (Article XII).
    - ``billing_portal_endpoint``: where the Stripe app's billing-portal view is mounted
      (ADR 0005). ``None`` for anyone with nothing current, because there is nothing to manage
      until a subscription exists (ADR 0007).
    - ``plans_url``: the plans page, which is not in the navigation.
    - ``plan_switch_endpoint``: where the Stripe app's plan-switch view is mounted, which opens
      the provider's plan-change screen (ADR 0008). ``None`` for anyone with nothing current.
    - ``provider_return``: set when the reader comes back from the provider (``?returned=N``) and
      nothing current shows yet, because the webhook can arrive after the reader is back. A dict
      of ``attempt`` and ``poll_url``, which is ``None`` once ``RETURN_POLL_LIMIT`` polls are
      spent. ``None`` otherwise.
    """

    #: How many times the subscription region polls for a payment to arrive after the reader
    #: comes back from the provider, before it stops and says to reload later.
    RETURN_POLL_LIMIT = 5

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the subscriptions and the ways onward from them."""
        context: dict[str, Any] = super().get_context_data(**kwargs)
        subscriptions = SubscriptionReader.for_user(self.request.user)
        context["provider_return"] = self.provider_return(subscriptions)
        namespace = self.request.resolver_match.namespace
        context["subscriptions"] = subscriptions
        context["billing_portal_endpoint"] = (
            reverse(f"{namespace}:stripe-billing-portal") if subscriptions else None
        )
        context["plan_switch_endpoint"] = (
            reverse(f"{namespace}:stripe-plan-switch") if subscriptions else None
        )
        context["plans_url"] = self.get_contribution().page_url("plans")
        return context

    def provider_return(self, subscriptions: Any) -> dict[str, Any] | None:
        """Whether the reader is waiting on a payment to arrive, and where to poll for it."""
        returned = self.request.GET.get("returned")
        if returned is None or subscriptions:
            return None
        attempt = int(returned) if returned.isdigit() and int(returned) > 0 else 1
        return {
            "attempt": attempt,
            "poll_url": f"{self.request.path}?returned={attempt + 1}"
            if attempt < self.RETURN_POLL_LIMIT
            else None,
        }


class PlansPageView(PaymentPageView):
    """The Stripe namespace's plans page: the provider's own pricing table, mounted.

    Open to every visitor, signed in or not, whatever they are subscribed to.

    Adds to the context:

    - ``pricing_table_id`` and ``publishable_key``: from ``settings.MVP_PAYMENTS`` at render
      time, ``None`` where not supplied (Article XIII).
    - ``client_reference_id``: for a signed-in person, the signed reference that ties their
      purchase to them (ADR 0011). ``None`` for a visitor who is not signed in.
    - ``customer_session_client_secret``: for a signed-in person who already has a Stripe
      customer, the secret that makes a purchase land on that customer. ``None`` otherwise.
    - ``sign_in_url``: for a visitor who is not signed in, the sign-in page, which returns here.
      ``None`` for a signed-in person.
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the pricing table's settings and what ties a purchase to this person."""
        context: dict[str, Any] = super().get_context_data(**kwargs)
        mvp_payments_settings = getattr(settings, "MVP_PAYMENTS", {})
        context["pricing_table_id"] = mvp_payments_settings.get(
            "STRIPE_PRICING_TABLE_ID"
        )
        context["publishable_key"] = mvp_payments_settings.get("STRIPE_PUBLISHABLE_KEY")
        context["client_reference_id"] = None
        context["customer_session_client_secret"] = None
        context["sign_in_url"] = None
        user = self.request.user
        if not user.is_authenticated:
            context["sign_in_url"] = redirect_to_login(self.request.get_full_path()).url
            return context
        customer_model = apps.get_model("mvp_payments_stripe", "Customer")
        context["client_reference_id"] = customer_model.client_reference(user)
        customer = customer_model.for_user(user)
        if customer is not None:
            context["customer_session_client_secret"] = (
                customer.pricing_table_client_secret()
            )
        return context
