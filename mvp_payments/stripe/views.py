"""The webhook Stripe calls, and the handoffs to Stripe's own pages."""

import logging

import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from stripe.params.billing_portal import SessionCreateParamsFlowData

from mvp_payments.contributions import APP_NAMESPACE

from .models import Customer

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook(request: HttpRequest) -> HttpResponse:
    """Verify a Stripe webhook, then bring the affected customer's records into step.

    The signature is checked before anything in the body is read. A verified event is a
    prompt, not a payload to trust: the records are rewritten from what Stripe holds now,
    so an event that arrives twice, late or out of order leaves the same rows. A function
    view, because nothing here is meant to be subclassed.

    Args:
        request: The POST Stripe sent.

    Returns:
        An empty response: 400 when the signature does not verify, 500 when Stripe could
        not be asked or the signing secret is not set (so Stripe sends the event again),
        and 200 otherwise, including for events about objects the app does not keep.
    """
    secret = getattr(settings, "MVP_PAYMENTS", {}).get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        # An empty key would let anyone sign a request, so nothing is verified against it.
        logger.error("MVP_PAYMENTS['STRIPE_WEBHOOK_SECRET'] is not set.")
        return HttpResponse(status=500)
    try:
        event = stripe.Webhook.construct_event(
            request.body, request.headers.get("Stripe-Signature"), secret
        )
    except (ValueError, stripe.SignatureVerificationError) as error:
        logger.warning("Refused a Stripe webhook: %s.", type(error).__name__)
        return HttpResponse(status=400)

    try:
        with transaction.atomic():
            customer = customer_for(event)
            if customer is not None:
                customer.sync()
    except stripe.StripeError as error:
        # Not logger.exception: Stripe's message can echo part of the secret key.
        logger.error(  # noqa: TRY400
            "Could not handle Stripe event %s: %s.", event.id, type(error).__name__
        )
        return HttpResponse(status=500)
    return HttpResponse()


def customer_for(event: stripe.Event) -> Customer | None:
    """Find the customer a verified event is about.

    Args:
        event: The verified event.

    Returns:
        The customer to sync, or ``None`` when the event is about nothing the app keeps.

    Raises:
        stripe.StripeError: When tying a checkout to a user needed Stripe and it failed.
    """
    event_object = event.data.object
    if event.type == "checkout.session.completed":
        return Customer.from_checkout(event_object.id)
    if event.type.startswith("customer.subscription."):
        return Customer.objects.filter(stripe_id=event_object.customer).first()
    if event.type == "customer.deleted":
        return Customer.objects.filter(stripe_id=event_object.id).first()
    return None


class BillingPortalView(LoginRequiredMixin, View):
    """Hand a signed-in customer to Stripe's hosted billing portal.

    Answers a POST with ``{"url": ...}``, which ``billing_portal.js`` follows. Only a stale
    page or a direct post reaches it without a customer, and creating one for whoever asks is
    what the page's suppression of the control exists to prevent (ADR 0007), so it answers 409.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Mint a portal session for this person's customer, or say why it could not be.

        Args:
            request: The signed-in person's POST.

        Returns:
            The portal address; 409 when there is no customer or nothing to open; 502 when
            Stripe could not be asked.
        """
        customer = Customer.for_user(request.user)
        if customer is None or not self.is_offered(customer):
            return JsonResponse({"detail": "Nothing to change."}, status=409)
        return_url = request.build_absolute_uri(
            reverse(f"{APP_NAMESPACE}:stripe-billing-return")
        )
        try:
            url = customer.portal_url(
                return_url, self.get_flow_data(customer, return_url)
            )
        except stripe.StripeError as error:
            # Not logger.exception: Stripe's message can echo part of the secret key.
            logger.error(  # noqa: TRY400
                "Could not open the Stripe billing portal for user %s: %s.",
                request.user.pk,
                type(error).__name__,
            )
            return JsonResponse(
                {"detail": "The billing portal is unavailable."}, status=502
            )
        return JsonResponse({"url": url})

    def is_offered(self, customer: Customer) -> bool:
        """Say whether there is a portal to open for this customer.

        Args:
            customer: The signed-in person's customer.

        Returns:
            Always ``True``: the portal's home is for any customer.
        """
        return True

    def get_flow_data(
        self, customer: Customer, return_url: str
    ) -> SessionCreateParamsFlowData | None:
        """Choose the portal flow to open on.

        Args:
            customer: The signed-in person's customer.
            return_url: Where Stripe sends the reader afterwards.

        Returns:
            ``None``: the portal's home.
        """
        return None


class PlanSwitchView(BillingPortalView):
    """Open the portal on the plan-change screen for this person's subscription.

    The user subscriptions page's "Switch plans" control posts here. The pricing table is the wrong
    place for a subscriber: buying from it starts a second subscription beside the first
    (ADR 0008). With several subscriptions there is no one to open on, so the portal's home
    lets them pick.
    """

    def is_offered(self, customer: Customer) -> bool:
        """Offer the switch only to a customer with something subscribed.

        Args:
            customer: The signed-in person's customer.

        Returns:
            Whether the customer has a subscription that counts as subscribed.
        """
        return customer.subscriptions.subscribed().exists()

    def get_flow_data(
        self, customer: Customer, return_url: str
    ) -> SessionCreateParamsFlowData | None:
        """Deep-link the session to changing the customer's subscription.

        Args:
            customer: The signed-in person's customer.
            return_url: Where Stripe sends the reader afterwards.

        Returns:
            The plan-change flow, or ``None`` when there is not exactly one subscription.
        """
        return customer.plan_change_flow(return_url)


class BillingReturnView(LoginRequiredMixin, View):
    """Where the portal sends a reader back to: refresh, then the user subscriptions page.

    A change made in the portal reaches the site through Stripe's webhook, which can arrive
    after the reader does, and a development server is not reachable from Stripe at all. So
    the customer is synchronised on the way back. It lands with ``?returned=1``, so if the
    change has still not arrived the page says it is being confirmed and polls for it.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """Bring the person's subscriptions up to date, then go back to the page.

        Args:
            request: The signed-in person's GET.

        Returns:
            A redirect to the user subscriptions page. A Stripe failure does not stop it: the
            webhook is still coming.
        """
        customer = Customer.for_user(request.user)
        if customer is not None:
            try:
                customer.sync()
            except stripe.StripeError as error:
                logger.error(  # noqa: TRY400
                    "Could not refresh user %s from Stripe: %s.",
                    request.user.pk,
                    type(error).__name__,
                )
        return redirect(reverse(f"{APP_NAMESPACE}:stripe-subscription") + "?returned=1")


class CheckoutView(LoginRequiredMixin, View):
    """SKETCH (FS-005): where a plan's way to buy posts to.

    The build creates a Stripe checkout session here for the chosen price, with the
    person's signed reference and Stripe customer, and redirects to it (FR-007). The
    sketch only returns to the page the plan was chosen on, saying so.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Go back to where the plan was chosen, naming the price that would be bought."""
        return_to = request.POST.get("return_to") or "/"
        if not return_to.startswith("/") or return_to.startswith("//"):
            return_to = "/"
        price = request.POST.get("price", "")
        return redirect(f"{return_to}?sketch_checkout={price}")
