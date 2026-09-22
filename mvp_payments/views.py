"""The page view every contribution's pages are built from.

One view class rather than one per page: each :class:`~mvp_payments.contributions.Page`
becomes an instance of this view, built through ``as_view(page=...)``, taking its
template and heading from the page it was built for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise
from mvp.views import MVPTemplateView

from .namespaces.drf_stripe_records import SubscriptionReader

if TYPE_CHECKING:
    from .contributions import Page


class PaymentPageView(LoginRequiredMixin, MVPTemplateView):
    """One page a namespace contributes, following ``AccountCenterView``'s shape.

    ``page`` must be set through ``as_view(page=...)`` — mirroring how
    ``BaseTemplateNameMixin`` requires ``base_template_name`` — because this
    class is never used directly, only built once per declared ``Page``.
    """

    page: Page | None = None

    def get_page(self) -> Page:
        if self.page is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} requires `page` to be set, via as_view(page=...)."
            )
        return self.page

    def get_template_names(self) -> list[str]:
        return [self.get_page().template_name]

    def get_page_title(self) -> str | Promise:
        return self.get_page().label


class SubscriptionPageView(PaymentPageView):
    """The drf-stripe namespace's subscription page: what the signed-in person is on.

    Adds ``subscriptions`` to the context — the reader's current subscriptions for this request's
    person, computed at render time rather than the backend importing anything (Article XIII).
    """

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)
        context["subscriptions"] = SubscriptionReader.for_user(self.request.user)
        return context
