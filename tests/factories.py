"""One factory per model the pages read (Article I).

Every ``Meta.model`` is a string, so factory_boy resolves it through Django's own application
registry the same way the package does.
"""

import factory
from django.contrib.auth.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Not a Stripe model — the plumbing a customer needs a person to attach to."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"person-{n}")


class StripeCustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "mvp_payments_stripe.Customer"

    user = factory.SubFactory(UserFactory)
    stripe_id = factory.Sequence(lambda n: f"cus_app_{n}")


class StripeSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "mvp_payments_stripe.Subscription"

    customer = factory.SubFactory(StripeCustomerFactory)
    stripe_id = factory.Sequence(lambda n: f"sub_app_{n}")
    status = "active"
    price_id = factory.Sequence(lambda n: f"price_app_{n}")
    product_name = "Pro"
    amount = 2000
    currency = "usd"
    interval = "month"
    interval_count = 1
