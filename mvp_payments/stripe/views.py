"""The webhook Stripe calls when something about a customer or subscription changes."""

import logging

import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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
            customer = _customer_for(event)
            if customer is not None:
                customer.sync()
    except stripe.StripeError as error:
        # Not logger.exception: Stripe's message can echo part of the secret key.
        logger.error(  # noqa: TRY400
            "Could not handle Stripe event %s: %s.", event.id, type(error).__name__
        )
        return HttpResponse(status=500)
    return HttpResponse()


def _customer_for(event: stripe.Event) -> Customer | None:
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
