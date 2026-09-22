"""Create the accounts the demo signs in with, and what each of them is subscribed to.

Development only. The demo project is never deployed, and these passwords are
written here in plain sight precisely so nobody mistakes them for real ones.

The backend's models are reached through ``apps.get_model`` rather than imported, matching the
rule ``mvp_payments/`` itself follows (Article XIII) — the demo shows the package working the same
way a host project would use it, not a shortcut available only here.
"""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

PASSWORD = "password"

ACCOUNTS = [
    {"username": "regular.user", "email": "regular.user@example.com"},
    {"username": "staff.user", "email": "staff.user@example.com", "is_staff": True},
    {
        "username": "super.user",
        "email": "super.user@example.com",
        "is_staff": True,
        "is_superuser": True,
    },
]


class Command(BaseCommand):
    """Seed the demo project with one account per role, and subscriptions to look at."""

    help = "Create the demo's sign-in accounts and their subscriptions, one per role."

    def handle(self, *args, **options):
        """Create each account if it is missing, and reset its password either way."""
        user_model = get_user_model()
        for account in ACCOUNTS:
            username = account["username"]
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={k: v for k, v in account.items() if k != "username"},
            )
            user.set_password(PASSWORD)
            user.save()
            verb = "created" if created else "reset"
            self.stdout.write(f"{verb} {username} ({account['email']})")

        self._seed_subscriptions(user_model)

    def _seed_subscriptions(self, user_model):
        """Give the demo something for the subscription page to show.

        ``regular.user`` gets one active subscription covering two priced items in different
        currencies, on products that carry a feature each. ``staff.user`` gets a subscription the
        backend counts as trialing. ``super.user`` is left with no ``StripeUser`` row at all, so
        the empty state (US-4) is reachable without editing anything. A fourth, unlisted person
        gets a subscription of their own — nothing this command creates for ``regular.user`` may
        ever show it, which is the cross-user guarantee the page's own tests hold separately.
        """
        stripe_user_model = apps.get_model("drf_stripe", "StripeUser")
        feature_model = apps.get_model("drf_stripe", "Feature")
        product_model = apps.get_model("drf_stripe", "Product")
        product_feature_model = apps.get_model("drf_stripe", "ProductFeature")
        price_model = apps.get_model("drf_stripe", "Price")
        subscription_model = apps.get_model("drf_stripe", "Subscription")
        subscription_item_model = apps.get_model("drf_stripe", "SubscriptionItem")

        priority_support, _ = feature_model.objects.get_or_create(
            feature_id="feature_demo_priority_support",
            defaults={"description": "Priority support"},
        )
        advanced_reports, _ = feature_model.objects.get_or_create(
            feature_id="feature_demo_advanced_reports",
            defaults={"description": "Advanced reports"},
        )

        basic, _ = product_model.objects.get_or_create(
            product_id="prod_demo_basic",
            defaults={"active": True, "name": "Basic", "description": "The basic plan"},
        )
        premium, _ = product_model.objects.get_or_create(
            product_id="prod_demo_premium",
            defaults={
                "active": True,
                "name": "Premium",
                "description": "The premium plan",
            },
        )
        product_feature_model.objects.get_or_create(
            product=basic, feature=priority_support
        )
        product_feature_model.objects.get_or_create(
            product=premium, feature=advanced_reports
        )

        basic_price, _ = price_model.objects.get_or_create(
            price_id="price_demo_basic_usd",
            defaults={
                "product": basic,
                "nickname": "Basic monthly",
                "price": 2000,
                "freq": "month_1",
                "active": True,
                "currency": "USD",
            },
        )
        premium_price, _ = price_model.objects.get_or_create(
            price_id="price_demo_premium_jpy",
            defaults={
                "product": premium,
                "nickname": "Premium monthly",
                "price": 500000,
                "freq": "month_1",
                "active": True,
                "currency": "JPY",
            },
        )

        regular_user = user_model.objects.get(username="regular.user")
        regular_stripe_user, _ = stripe_user_model.objects.get_or_create(
            user=regular_user, defaults={"customer_id": "cus_demo_regular"}
        )
        regular_subscription, _ = subscription_model.objects.get_or_create(
            subscription_id="sub_demo_regular",
            defaults={
                "stripe_user": regular_stripe_user,
                "status": "active",
                "cancel_at_period_end": False,
            },
        )
        subscription_item_model.objects.get_or_create(
            sub_item_id="si_demo_regular_basic",
            defaults={
                "subscription": regular_subscription,
                "price": basic_price,
                "quantity": 1,
            },
        )
        subscription_item_model.objects.get_or_create(
            sub_item_id="si_demo_regular_premium",
            defaults={
                "subscription": regular_subscription,
                "price": premium_price,
                "quantity": 1,
            },
        )

        staff_user = user_model.objects.get(username="staff.user")
        staff_stripe_user, _ = stripe_user_model.objects.get_or_create(
            user=staff_user, defaults={"customer_id": "cus_demo_staff"}
        )
        staff_subscription, _ = subscription_model.objects.get_or_create(
            subscription_id="sub_demo_staff",
            defaults={
                "stripe_user": staff_stripe_user,
                "status": "trialing",
                "cancel_at_period_end": False,
            },
        )
        subscription_item_model.objects.get_or_create(
            sub_item_id="si_demo_staff_basic",
            defaults={
                "subscription": staff_subscription,
                "price": basic_price,
                "quantity": 1,
            },
        )

        other_user, _ = user_model.objects.get_or_create(
            username="other.subscriber",
            defaults={"email": "other.subscriber@example.com"},
        )
        other_user.set_password(PASSWORD)
        other_user.save()
        other_stripe_user, _ = stripe_user_model.objects.get_or_create(
            user=other_user, defaults={"customer_id": "cus_demo_other"}
        )
        other_subscription, _ = subscription_model.objects.get_or_create(
            subscription_id="sub_demo_other",
            defaults={
                "stripe_user": other_stripe_user,
                "status": "active",
                "cancel_at_period_end": False,
            },
        )
        subscription_item_model.objects.get_or_create(
            sub_item_id="si_demo_other_basic",
            defaults={
                "subscription": other_subscription,
                "price": basic_price,
                "quantity": 1,
            },
        )
