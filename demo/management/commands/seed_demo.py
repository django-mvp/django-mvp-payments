"""Create the accounts the demo signs in with, and what each of them is subscribed to.

Development only. The demo project is never deployed, and these passwords are
written here in plain sight precisely so nobody mistakes them for real ones.

The backend's models are reached through ``apps.get_model`` rather than imported, matching the
rule ``mvp_payments/`` itself follows (Article XIII) — the demo shows the package working the same
way a host project would use it, not a shortcut available only here.
"""

import contextlib
import io

import stripe
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

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


#: Who gets a real sandbox subscription, and for how many trial days. ``super.user`` is left
#: out so the empty state stays reachable.
SANDBOX_SUBSCRIBERS = [
    ("regular.user", None),
    ("staff.user", 14),
    ("other.subscriber", None),
]

#: Statuses under which a sandbox subscription still counts as the one a person is on.
LIVE_STATUSES = {"active", "trialing", "past_due", "unpaid", "incomplete"}


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

        if getattr(settings, "DEV_ENV", {}).get("STRIPE_TEST_SECRET_KEY"):
            self.seed_sandbox_subscriptions(user_model)
        else:
            self._seed_subscriptions(user_model)

    def seed_sandbox_subscriptions(self, user_model):
        """Real subscriptions in the provider's sandbox, pulled back into the backend's records.

        Used instead of the invented records whenever ``demo/.env`` holds a sandbox key. The
        provider's portal shows, switches and cancels only subscriptions it holds itself, so a
        subscription that exists only in this database reaches the portal as a customer with
        nothing on it.

        ``regular.user`` and the unlisted ``other.subscriber`` get an active subscription and
        ``staff.user`` a trialing one, each on the cheapest monthly plan in the sandbox and paid
        with the provider's test card. ``super.user`` gets nothing, as offline. A person who
        already has a live subscription there keeps it, so running this twice creates nothing
        new and a plan switched in the portal is not switched back.

        Invented subscriptions left by an earlier offline run are removed, so the page never
        shows one beside a real one. Products, prices and subscriptions are then read back
        through the backend's own synchronisation, exactly as its management commands do.
        """
        from drf_stripe.stripe_api.products import stripe_api_update_products_prices
        from drf_stripe.stripe_api.subscriptions import stripe_api_update_subscriptions

        stripe.api_key = settings.DEV_ENV["STRIPE_TEST_SECRET_KEY"]
        stripe_user_model = apps.get_model("drf_stripe", "StripeUser")
        subscription_model = apps.get_model("drf_stripe", "Subscription")

        other_user, _ = user_model.objects.get_or_create(
            username="other.subscriber",
            defaults={"email": "other.subscriber@example.com"},
        )
        other_user.set_password(PASSWORD)
        other_user.save()

        price_id = self.cheapest_monthly_price()
        for username, trial_days in SANDBOX_SUBSCRIBERS:
            user = user_model.objects.get(username=username)
            stripe_user = self._stripe_user(stripe_user_model, user, None)
            self.ensure_sandbox_subscription(
                stripe_user.customer_id, price_id, trial_days
            )

        subscription_model.objects.filter(
            subscription_id__startswith="sub_demo_"
        ).delete()
        with contextlib.redirect_stdout(io.StringIO()):
            stripe_api_update_products_prices()
            stripe_api_update_subscriptions(
                status="all", ignore_new_user_creation_errors=True
            )
        self.stdout.write("pulled sandbox products, prices and subscriptions")

    def cheapest_monthly_price(self):
        """The sandbox's cheapest active monthly price, so every run picks the same one."""
        prices = [
            price
            for price in stripe.Price.list(
                active=True, type="recurring", limit=100
            ).data
            if price.recurring.interval == "month"
            and price.recurring.interval_count == 1
        ]
        if not prices:
            raise CommandError(
                "The sandbox has no active monthly price to subscribe the demo accounts to."
            )
        return min(prices, key=lambda price: price.unit_amount or 0).id

    def ensure_sandbox_subscription(self, customer_id, price_id, trial_days):
        """Subscribe this customer with the provider's test card, unless they are already."""
        live = [
            subscription
            for subscription in stripe.Subscription.list(
                customer=customer_id, status="all", limit=100
            ).data
            if subscription.status in LIVE_STATUSES
        ]
        if live:
            return
        payment_method = stripe.PaymentMethod.attach(
            "pm_card_visa", customer=customer_id
        )
        stripe.Customer.modify(
            customer_id, invoice_settings={"default_payment_method": payment_method.id}
        )
        options = {"trial_period_days": trial_days} if trial_days else {}
        stripe.Subscription.create(
            customer=customer_id, items=[{"price": price_id}], **options
        )

    def _customer_id(self, email, fallback):
        """A provider customer for this person, real where the demo has credentials.

        The portal a subscriber is handed to is minted by the provider for a customer it knows
        about, so an invented identifier gets as far as the button and no further: the control
        posts, the backend asks the provider, and the reader is told the portal could not be
        reached. With a sandbox key in ``demo/.env`` this creates a customer there, or reuses the
        one already created for that address, and the handoff can be followed all the way to the
        provider's own page.

        Without credentials it returns the invented identifier and the demo behaves exactly as a
        project that has not configured its backend, which is worth being able to look at too.
        """
        secret = getattr(settings, "DEV_ENV", {}).get("STRIPE_TEST_SECRET_KEY")
        if not secret:
            return fallback

        stripe.api_key = secret
        existing = stripe.Customer.list(email=email, limit=1).data
        if existing:
            return existing[0].id
        return stripe.Customer.create(email=email, name=email.partition("@")[0]).id

    def _stripe_user(self, stripe_user_model, user, fallback_customer_id):
        """This person's backend customer record, with its identifier kept current.

        ``get_or_create`` applies its defaults only when it creates, so a demo database seeded
        before credentials were configured would keep its invented identifier forever and the
        portal would go on failing for reasons nothing on screen explains.
        """
        customer_id = self._customer_id(user.email, fallback_customer_id)
        stripe_user, created = stripe_user_model.objects.get_or_create(
            user=user, defaults={"customer_id": customer_id}
        )
        if not created and stripe_user.customer_id != customer_id:
            stripe_user.customer_id = customer_id
            stripe_user.save(update_fields=["customer_id"])
        return stripe_user

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
        regular_stripe_user = self._stripe_user(
            stripe_user_model, regular_user, "cus_demo_regular"
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
        staff_stripe_user = self._stripe_user(
            stripe_user_model, staff_user, "cus_demo_staff"
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
        other_stripe_user = self._stripe_user(
            stripe_user_model, other_user, "cus_demo_other"
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
