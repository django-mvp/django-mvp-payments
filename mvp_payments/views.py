"""The page view every contribution's pages are built from.

One view class rather than one per page: each :class:`~mvp_payments.contributions.Page`
becomes an instance of this view, built through ``as_view(page=...)``, taking its
template and heading from the page it was built for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise
from mvp.views import MVPTemplateView

from .namespaces.drf_stripe_records import SubscriptionReader

if TYPE_CHECKING:
    from .contributions import Contribution, Page


class PaymentPageView(LoginRequiredMixin, MVPTemplateView):
    """One page a namespace contributes, following ``AccountCenterView``'s shape.

    Never used directly, only built once per declared ``Page`` through ``as_view()``.

    Attributes:
        page: The page this view renders, set through ``as_view(page=...)``.
        contribution: The contribution the page belongs to, set through
            ``as_view(contribution=...)``. It is how a page addresses a sibling that
            is not in the navigation.
    """

    page: Page | None = None
    contribution: Contribution | None = None

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
    """The drf-stripe namespace's subscription page: what the signed-in person is on.

    Adds to the context:

    - ``subscriptions``: this person's current subscriptions, read at render time (Article XII).
    - ``billing_portal_endpoint``: where the backend's billing-portal endpoint is mounted, from
      ``settings.MVP_PAYMENTS`` (ADR 0005). ``None`` for anyone with nothing current, because the
      endpoint creates a provider customer for whoever posts to it (ADR 0007).
    - ``plans_url``: the plans page, which is not in the navigation.
    - ``plan_switch_endpoint``: the project's endpoint opening the provider's plan-change screen,
      from the same settings (ADR 0008). ``None`` for anyone with nothing current.
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the subscriptions and the ways onward from them."""
        context: dict[str, Any] = super().get_context_data(**kwargs)
        subscriptions = SubscriptionReader.for_user(self.request.user)
        mvp_payments_settings = getattr(settings, "MVP_PAYMENTS", {})
        context["subscriptions"] = subscriptions
        context["billing_portal_endpoint"] = (
            mvp_payments_settings.get("DRF_STRIPE_BILLING_PORTAL")
            if subscriptions
            else None
        )
        context["plan_switch_endpoint"] = (
            mvp_payments_settings.get("DRF_STRIPE_PLAN_SWITCH")
            if subscriptions
            else None
        )
        context["plans_url"] = self.get_contribution().page_url("plans")
        return context


class PlansPageView(PaymentPageView):
    """The drf-stripe namespace's plans page: the provider's own pricing table, mounted.

    Adds to the context:

    - ``pricing_table_id`` and ``publishable_key``: from ``settings.MVP_PAYMENTS`` at render
      time, ``None`` where not supplied (Article XIII).
    - ``subscriptions``: this person's current subscriptions. A subscriber is sent to the
      subscription page to switch instead of shown the pricing table (ADR 0008).
    - ``subscription_url``: the subscription page.
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the pricing table's settings and this person's subscriptions."""
        context: dict[str, Any] = super().get_context_data(**kwargs)
        context["subscriptions"] = SubscriptionReader.for_user(self.request.user)
        context["subscription_url"] = self.get_contribution().page_url("subscription")
        mvp_payments_settings = getattr(settings, "MVP_PAYMENTS", {})
        context["pricing_table_id"] = mvp_payments_settings.get(
            "DRF_STRIPE_PRICING_TABLE_ID"
        )
        context["publishable_key"] = mvp_payments_settings.get(
            "DRF_STRIPE_PUBLISHABLE_KEY"
        )
        return context
