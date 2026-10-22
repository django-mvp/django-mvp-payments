"""The webhook Stripe calls, and the handoffs to Stripe's own pages."""

import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from stripe.params.billing_portal import SessionCreateParamsFlowData

from mvp_payments.contributions import APP_NAMESPACE

from .catalogue import Catalogue
from .models import Customer, Subscription

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def webhook(request: HttpRequest) -> HttpResponse:
    """Verify a Stripe webhook, then bring the affected records into step.

    The signature is checked before anything in the body is read. A verified event is a
    prompt, not a payload to trust: the records are rewritten from what Stripe holds now,
    so an event that arrives twice, late or out of order leaves the same rows. A product or
    price event forgets the cached catalogue, so the plans page reads Stripe again. A function
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

    if event.type.startswith(("product.", "price.")):
        Catalogue.clear()

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

    The user subscriptions page's "Switch plans" control posts here. The plans page is the wrong
    place for a subscriber to change plan: buying from it starts a second subscription beside the
    first (ADR 0008). With several subscriptions there is no one to open on, so the portal's home
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
            request: The signed-in person's GET. Coming back from checkout it carries
                ``session_id``, which ties a first purchase to the person when the webhook
                has not yet done so.

        Returns:
            A redirect to the user subscriptions page. A Stripe failure does not stop it: the
            webhook is still coming.
        """
        try:
            customer = self.get_customer(request)
            if customer is not None:
                customer.sync()
        except stripe.StripeError as error:
            logger.error(  # noqa: TRY400
                "Could not refresh user %s from Stripe: %s.",
                request.user.pk,
                type(error).__name__,
            )
        return redirect(reverse(f"{APP_NAMESPACE}:stripe-subscription") + "?returned=1")

    def get_customer(self, request: HttpRequest) -> Customer | None:
        """Find the customer to refresh, tying a checkout's purchase to the person if need be.

        Args:
            request: The signed-in person's GET.

        Returns:
            The person's customer. When they have none and the request names a checkout
            session, the customer that session created, if it was made for this person.

        Raises:
            stripe.StripeError: When Stripe could not be asked, or refused.
        """
        customer = Customer.for_user(request.user)
        session_id = request.GET.get("session_id")
        if customer is None and session_id:
            customer = Customer.from_checkout(session_id)
            if customer is not None and customer.user_id != request.user.pk:
                return None
        return customer


class CheckoutView(LoginRequiredMixin, View):
    """Start a Stripe checkout for the plan a signed-in person chose.

    A POST of the ``price`` chosen and a ``return_to`` path on this site, from the plans
    page. The price must be one the catalogue offers. Every way it can fail adds a message
    and sends the reader back to ``return_to``: the plans page is where they chose, and
    ``mvp/base.html`` shows the message above it.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """Send the reader to Stripe's checkout for the price, or back with a message.

        Args:
            request: The signed-in person's POST.

        Returns:
            A redirect to Stripe's checkout; to the user subscriptions page when the person
            already holds the price; otherwise back to ``return_to``.
        """
        return_to = self.get_return_to(request)
        if Catalogue.prices() is None:
            messages.error(
                request,
                _("The plans can't be shown right now. Please try again shortly."),
            )
            return redirect(return_to)
        price_id = request.POST.get("price", "")
        if Catalogue.price(price_id) is None:
            messages.warning(request, _("That plan is no longer on offer."))
            return redirect(return_to)
        if (
            Subscription.objects.for_user(request.user)
            .current()
            .filter(price_id=price_id)
            .exists()
        ):
            return redirect(f"{APP_NAMESPACE}:stripe-subscription")
        success_url = (
            request.build_absolute_uri(
                reverse(f"{APP_NAMESPACE}:stripe-billing-return")
            )
            + "?session_id={CHECKOUT_SESSION_ID}"
        )
        try:
            url = Customer.start_checkout(
                request.user,
                price_id,
                success_url,
                request.build_absolute_uri(return_to),
            )
        except stripe.StripeError as error:
            # Not logger.exception: Stripe's message can echo part of the secret key.
            logger.error(  # noqa: TRY400
                "Could not start a Stripe checkout for user %s: %s.",
                request.user.pk,
                type(error).__name__,
            )
            messages.error(
                request,
                _("We couldn't start the checkout. Please try again shortly."),
            )
            return redirect(return_to)
        return redirect(url)

    def get_return_to(self, request: HttpRequest) -> str:
        """Choose where to send the reader when checkout does not start.

        Args:
            request: The POST, whose ``return_to`` names the page the plan was chosen on.

        Returns:
            ``return_to`` when it is a path on this site, otherwise the plans page, or the
            site's root when the project has not mounted one.
        """
        return_to = request.POST.get("return_to", "")
        if return_to and url_has_allowed_host_and_scheme(
            return_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return return_to
        try:
            return reverse("payments_plans:stripe-plans")
        except NoReverseMatch:
            return "/"
