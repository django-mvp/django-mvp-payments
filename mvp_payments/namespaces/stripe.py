"""The Stripe namespace's contribution.

One navigation entry, Subscription, under a Billing group. The plans page is a
public page of its own, outside the Account Center (``mvp_payments.plans_urls``). A group
holding a single entry is deliberate, and leaves an obvious place for invoices
and payment methods to arrive later.
"""

from django.utils.translation import gettext_lazy as _

from mvp_payments.contributions import Contribution, Page
from mvp_payments.views import SubscriptionPageView

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
    ),
    card_template="mvp_payments/card.html",
    group_label=_("Billing"),
)
