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

    ``page`` must be set through ``as_view(page=...)`` — mirroring how
    ``BaseTemplateNameMixin`` requires ``base_template_name`` — because this
    class is never used directly, only built once per declared ``Page``.
    ``contribution`` arrives the same way, and is how a page addresses a
    sibling: not every page is in the navigation any more, so the ones that
    are have to be able to link to the ones that are not.
    """

    page: Page | None = None
    contribution: Contribution | None = None

    def get_page(self) -> Page:
        if self.page is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} requires `page` to be set, via as_view(page=...)."
            )
        return self.page

    def get_contribution(self) -> Contribution:
        if self.contribution is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} requires `contribution` to be set, "
                "via as_view(contribution=...)."
            )
        return self.contribution

    def get_template_names(self) -> list[str]:
        return [self.get_page().template_name]

    def get_page_title(self) -> str | Promise:
        return self.get_page().label


class SubscriptionPageView(PaymentPageView):
    """The drf-stripe namespace's subscription page: what the signed-in person is on.

    Adds ``subscriptions`` to the context — the reader's current subscriptions for this request's
    person, computed at render time rather than the backend importing anything (Article XIII).

    Also adds ``billing_portal_endpoint``: where the backend's own billing-portal endpoint is
    mounted, read from ``settings.MVP_PAYMENTS`` at render time rather than assumed (D3, FR-006).
    Suppressed for anyone with nothing current, never merely disabled — the backend's endpoint
    creates a customer at the provider for whoever posts to it, so offering the control to someone
    who never subscribed would create one by their clicking it (D5).

    And ``plans_url``: the plans page is no longer in the Account Center's navigation, so this
    page carries the way to it. Offered to everyone, unlike the portal, because somebody with no
    subscription is exactly who needs it.
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)
        subscriptions = SubscriptionReader.for_user(self.request.user)
        context["subscriptions"] = subscriptions
        context["billing_portal_endpoint"] = (
            getattr(settings, "MVP_PAYMENTS", {}).get("DRF_STRIPE_BILLING_PORTAL")
            if subscriptions
            else None
        )
        context["plans_url"] = self.get_contribution().page_url("plans")
        return context


class PlansPageView(PaymentPageView):
    """The drf-stripe namespace's plans page: the provider's own pricing table, mounted.

    Adds ``pricing_table_id`` and ``publishable_key`` to the context, read from
    ``settings.MVP_PAYMENTS`` at render time rather than assumed (Article XIV). Both default
    to ``None`` where the setting is not supplied — the surface a project overriding this
    page's template relies on.
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)
        mvp_payments_settings = getattr(settings, "MVP_PAYMENTS", {})
        context["pricing_table_id"] = mvp_payments_settings.get(
            "DRF_STRIPE_PRICING_TABLE_ID"
        )
        context["publishable_key"] = mvp_payments_settings.get(
            "DRF_STRIPE_PUBLISHABLE_KEY"
        )
        return context
