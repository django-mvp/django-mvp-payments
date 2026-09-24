import contextlib
import io

from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from mvp.views import MVPTemplateView


class HomeView(MVPTemplateView):
    """What this package is, and where the component pages will appear."""

    template_name = "demo/home.html"
    page_title = "Home"
    page_subtitle = "Payment and subscription interfaces as Cotton components"
    breadcrumbs = [{"text": "Home"}]


class PlansUnconfiguredView(MVPTemplateView):
    """The package's own Plans template, reached with neither configured value
    in context (US-4 scenarios 1 and 2).

    This route and its template belong to the demonstration project, not the
    package: nothing under ``mvp_payments/`` knows this view exists.
    """

    template_name = "demo/plans_unconfigured.html"
    page_title = "Plans, unconfigured"
    breadcrumbs = [{"text": "Home", "href": "/"}, {"text": "Plans, unconfigured"}]


class NoLibraryView(MVPTemplateView):
    """The pricing table component on a page whose provider library never
    arrived (US-4 scenario 3) — the demonstration project's own route."""

    template_name = "demo/no_library.html"
    page_title = "Library never arrived"
    breadcrumbs = [{"text": "Home", "href": "/"}, {"text": "Library never arrived"}]


class BillingPortalView(LoginRequiredMixin, View):
    """Hand a signed-in subscriber to the provider's hosted billing portal.

    The backend ships an endpoint for exactly this, and this demo mounted it, but it raises for
    everybody who has used it before. ``get_or_create_stripe_user(user_id=...)`` looks a customer
    record up by ``(user_id, customer_id=None)``; the first call creates that record and then
    fills the second field in, so every call after it matches nothing, tries to insert a second
    record for a person who already has one, and the database refuses. Open on the backend's own
    tracker.

    A host project cannot wait for that, so it does the two things the backend's endpoint does
    either side of the broken lookup: read the customer identifier the backend already keeps, and
    ask the provider for a session. This is what a real project would have to write today, which
    is the reason it is written here rather than worked around in the page.

    ``mvp_payments`` itself may not contain this. It reaches a provider only through a backend's
    HTTP endpoints and imports no provider SDK at all, which Article XII makes absolute and
    ``tests/test_app.py`` enforces. A demo is a host project and is bound by neither.

    The provider's key, its API version and the address to come back to are all read from the
    backend's own configuration, so this holds no settings of its own and cannot drift from the
    endpoint it stands in for.
    """

    def post(self, request):
        """Mint a portal session for this person, or say that it could not be reached."""
        from drf_stripe.stripe_api.api import stripe_api

        stripe_user_model = apps.get_model("drf_stripe", "StripeUser")
        stripe_user = stripe_user_model.objects.filter(
            user=request.user, customer_id__isnull=False
        ).first()

        # Nobody without a customer record at the provider has a portal to be sent to, and the
        # control is already absent for them. Reaching here anyway means a stale page or a direct
        # post, and creating a customer for whoever asks is how the backend's endpoint earned
        # that suppression in the first place (D5).
        if stripe_user is None:
            return JsonResponse({"detail": "No customer record."}, status=409)

        return_url = request.build_absolute_uri(reverse("billing-return"))
        options = self.session_options(request, return_url)
        if options is None:
            return JsonResponse({"detail": "Nothing to change."}, status=409)
        session = stripe_api.billing_portal.Session.create(
            customer=stripe_user.customer_id, return_url=return_url, **options
        )
        return JsonResponse({"url": session.url})

    def session_options(self, request, return_url):
        """Anything beyond the customer and the way back. The whole portal needs nothing."""
        return {}


class PlanSwitchView(BillingPortalView):
    """Open the provider's portal directly on the plan-change screen for this person's plan.

    The subscription page's "Switch plans" control posts here. The provider's pricing table is
    the wrong place for a subscriber: it cannot show which plan they are on, and buying from it
    starts a second subscription beside the first. The portal changes the one they have, showing
    the current plan and the price difference, and only offers plans the portal's own settings
    in the provider's dashboard allow switching to.

    Answers 409 for somebody with no current subscription, who has nothing to switch from.
    """

    def session_options(self, request, return_url):
        """Deep-link the session to changing this person's current subscription."""
        from drf_stripe.stripe_api.subscriptions import list_user_subscriptions

        subscription = list_user_subscriptions(request.user.id).first()
        if subscription is None:
            return None
        return {
            "flow_data": {
                "type": "subscription_update",
                "subscription_update": {"subscription": subscription.subscription_id},
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": return_url},
                },
            }
        }


class BillingReturnView(LoginRequiredMixin, View):
    """Where the provider's portal sends a reader back to: refresh, then the subscription page.

    A change made in the portal reaches a project through the provider's webhooks, and a
    development server is not reachable from the provider without a forwarding tool running
    beside it. So the demo asks the provider for the current state on the way back instead, using
    the backend's own synchronisation, and the subscription page shows the plan the reader just
    chose. A deployed project receives webhooks and needs none of this.

    It arrives with ``?returned=1``, so if the provider still has not caught up the page says a
    change is on its way rather than showing the state from before it.
    """

    def get(self, request):
        """Pull subscriptions from the provider into the backend's records, then go back."""
        from drf_stripe.stripe_api.subscriptions import stripe_api_update_subscriptions

        with contextlib.redirect_stdout(io.StringIO()):
            stripe_api_update_subscriptions(
                status="all", ignore_new_user_creation_errors=True
            )
        return redirect(reverse("payments:drf-stripe-subscription") + "?returned=1")
