"""The Stripe namespace's contribution.

One navigation entry, Subscription, under a Billing group. The plans page is
routed but not listed, because it is reached from a control on the
user subscriptions page. It is open to every visitor, signed in or not. A group
holding a single entry is deliberate, and leaves an obvious place for invoices
and payment methods to arrive later.
"""

from django.utils.translation import gettext_lazy as _

from mvp_payments.contributions import Contribution, Page
from mvp_payments.views import PlansPageView, SubscriptionPageView

stripe_contribution = Contribution(
    backend_app_name="mvp_payments.stripe",
    namespace="stripe",
    pages=(
        Page(
            slug="subscription",
            label=_("Subscription"),
            icon="subscription",
            template_name="mvp_payments/stripe/subscription.html",
            view=SubscriptionPageView,
        ),
        Page(
            slug="plans",
            label=_("Plans"),
            icon="plan",
            template_name="mvp_payments/stripe/plans.html",
            view=PlansPageView,
            in_navigation=False,
            login_required=False,
        ),
    ),
    card_template="mvp_payments/card.html",
    group_label=_("Billing"),
)
