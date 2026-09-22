"""One factory per backend model this page reads (Article X).

Every ``Meta.model`` is a string, so factory_boy resolves it through Django's own application
registry the same way the package it stands in for does — this module never imports ``drf_stripe``.
"""

import factory
from django.contrib.auth.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Not a backend model — the plumbing ``StripeUserFactory`` needs a person to attach to."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"person-{n}")


class StripeUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.StripeUser"

    user = factory.SubFactory(UserFactory)
    customer_id = factory.Sequence(lambda n: f"cus_{n}")


class FeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.Feature"

    feature_id = factory.Sequence(lambda n: f"feature_{n}")
    description = factory.Sequence(lambda n: f"Feature {n}")


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.Product"

    product_id = factory.Sequence(lambda n: f"prod_{n}")
    active = True
    name = factory.Sequence(lambda n: f"Product {n}")


class ProductFeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.ProductFeature"

    product = factory.SubFactory(ProductFactory)
    feature = factory.SubFactory(FeatureFactory)


class PriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.Price"

    price_id = factory.Sequence(lambda n: f"price_{n}")
    product = factory.SubFactory(ProductFactory)
    nickname = None
    price = 1000
    freq = "month_1"
    active = True
    currency = "USD"


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.Subscription"

    subscription_id = factory.Sequence(lambda n: f"sub_{n}")
    stripe_user = factory.SubFactory(StripeUserFactory)
    cancel_at_period_end = False
    status = "active"


class SubscriptionItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "drf_stripe.SubscriptionItem"

    sub_item_id = factory.Sequence(lambda n: f"si_{n}")
    subscription = factory.SubFactory(SubscriptionFactory)
    price = factory.SubFactory(PriceFactory)
    quantity = 1
