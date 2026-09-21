"""The drf-stripe-subscription namespace's contribution.

Three pages: the person's subscription, the plans available to them, and
their billing management (FR-007). Filling them in is a later roadmap item
(R2, R3, R5) — here they render their heading and nothing else.
"""

from django.utils.translation import gettext_lazy as _

from mvp_payments.contributions import Contribution, Page

drf_stripe = Contribution(
    backend_app_label="drf_stripe",
    namespace="drf-stripe",
    pages=(
        Page(
            slug="subscription",
            label=_("Subscription"),
            icon="subscription",
            template_name="mvp_payments/drf_stripe/subscription.html",
        ),
        Page(
            slug="plans",
            label=_("Plans"),
            icon="plan",
            template_name="mvp_payments/drf_stripe/plans.html",
        ),
        Page(
            slug="billing",
            label=_("Billing"),
            icon="payments",
            template_name="mvp_payments/drf_stripe/billing.html",
        ),
    ),
    card_template="mvp_payments/card.html",
)
