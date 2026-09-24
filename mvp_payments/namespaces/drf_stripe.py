"""The drf-stripe-subscription namespace's contribution.

One navigation entry, Subscription, under a Billing group. The plans page is
routed but not listed, because it is reached from a control on the
subscription page: somebody choosing a plan is already looking at the one
they are on. A group holding a single entry is deliberate, and leaves an
obvious place for invoices and payment methods to arrive later.
"""

from django.utils.translation import gettext_lazy as _

from mvp_payments.contributions import Contribution, Page
from mvp_payments.views import PlansPageView, SubscriptionPageView

drf_stripe = Contribution(
    backend_app_name="drf_stripe",
    namespace="drf-stripe",
    pages=(
        Page(
            slug="subscription",
            label=_("Subscription"),
            icon="subscription",
            template_name="mvp_payments/drf_stripe/subscription.html",
            view=SubscriptionPageView,
        ),
        Page(
            slug="plans",
            label=_("Plans"),
            icon="plan",
            template_name="mvp_payments/drf_stripe/plans.html",
            view=PlansPageView,
            in_navigation=False,
        ),
    ),
    card_template="mvp_payments/card.html",
    group_label=_("Billing"),
)
