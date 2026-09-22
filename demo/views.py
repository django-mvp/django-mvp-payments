from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
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

        return_url = request.build_absolute_uri(
            reverse("payments:drf-stripe-subscription")
        )
        session = stripe_api.billing_portal.Session.create(
            customer=stripe_user.customer_id, return_url=return_url
        )
        return JsonResponse({"url": session.url})
