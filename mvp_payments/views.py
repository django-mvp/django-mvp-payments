"""The page view every contribution's pages are built from.

One view class rather than one per page: each :class:`~mvp_payments.contributions.Page`
becomes an instance of this view, built through ``as_view(page=...)``, taking its
template and heading from the page it was built for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _
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
        context["plans_url"] = reverse("stripe-plans")
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


class PlansPageView(MVPTemplateView):
    """The Stripe plans page: the plans on offer, drawn from Stripe's catalogue.

    A public page, outside the Account Center, mounted wherever the project includes
    ``mvp_payments.plans_urls`` (``/plans/`` in the demo). Open to every visitor.

    Adds ``plans`` to the context: what the plans components read.
    """

    template_name = "mvp_payments/stripe/plans.html"
    page_title = _("Plans")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the plans for the person asking."""
        from mvp_payments.namespaces.stripe_plans import PlanChoices

        context: dict[str, Any] = super().get_context_data(**kwargs)
        context["plans"] = PlanChoices.for_request(self.request)
        return context
