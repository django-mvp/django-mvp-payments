"""Create the accounts the demo signs in with, and what each of them is subscribed to.

Development only. The demo project is never deployed, and these passwords are
written here in plain sight precisely so nobody mistakes them for real ones.

The Stripe app's models are reached through ``apps.get_model`` rather than imported, matching
the rule ``mvp_payments/`` itself follows (Article XII) — the demo shows the package working the
same way a host project would use it, not a shortcut available only here.
"""

from datetime import timedelta

import stripe
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

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

        catalogue = apps.get_app_config("mvp_payments_stripe").catalogue
        if getattr(settings, "DEV_ENV", {}).get("STRIPE_TEST_SECRET_KEY"):
            # The plans page reads the sandbox itself, so a catalogue primed offline goes.
            catalogue.clear()
            self.seed_sandbox_subscriptions(user_model)
        else:
            self.seed_offline_subscriptions(user_model)
            self.prime_catalogue(catalogue)

    def seed_sandbox_subscriptions(self, user_model):
        """Create real subscriptions in the provider's sandbox and read them back.

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
        shows one beside a real one. Each customer is then tied to its account and read back
        through the Stripe app's own ``sync()``.

        Args:
            user_model: The project's user model.
        """
        stripe.api_key = settings.DEV_ENV["STRIPE_TEST_SECRET_KEY"]

        other_user, _ = user_model.objects.get_or_create(
            username="other.subscriber",
            defaults={"email": "other.subscriber@example.com"},
        )
        other_user.set_password(PASSWORD)
        other_user.save()

        price_id = self.cheapest_monthly_price()
        sandbox_customers = {}
        for username, trial_days in SANDBOX_SUBSCRIBERS:
            user = user_model.objects.get(username=username)
            customer_id = self.customer_id_for(user.email, None)
            self.ensure_sandbox_subscription(customer_id, price_id, trial_days)
            sandbox_customers[user] = customer_id

        subscription_model = apps.get_model("mvp_payments_stripe", "Subscription")
        subscription_model.objects.filter(stripe_id__startswith="sub_demo_").delete()
        self.record_in_the_stripe_app(sandbox_customers)

    def record_in_the_stripe_app(self, sandbox_customers):
        """Tie each sandbox customer to its demo account in the Stripe app, then sync it.

        A real project ties a customer to a user when the user's own checkout completes. The
        demo's subscriptions are created here rather than through a checkout, so the tie is made
        here too, with the customer identifier Stripe gave the account. Everything else is read
        from Stripe by the app's own ``sync()``.

        Args:
            sandbox_customers: Each demo account and its sandbox customer identifier.
        """
        customer_model = apps.get_model("mvp_payments_stripe", "Customer")
        for user, stripe_id in sandbox_customers.items():
            customer, _ = customer_model.objects.update_or_create(
                user=user, defaults={"stripe_id": stripe_id}
            )
            customer.sync()
        self.stdout.write("recorded the sandbox subscriptions in the Stripe app")

    def cheapest_monthly_price(self):
        """Find the sandbox's cheapest active monthly price, so every run picks the same one.

        Returns:
            The price's identifier.

        Raises:
            CommandError: The sandbox has no active monthly price.
        """
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
        """Subscribe this customer with the provider's test card, unless they are already.

        Args:
            customer_id: The provider's identifier for the customer.
            price_id: The price to subscribe them to.
            trial_days: Days of trial to start with, or none.

        Returns:
            The customer's live subscription, existing or new.
        """
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

    def customer_id_for(self, email, fallback):
        """Find or create a provider customer for this person, where the demo has credentials.

        The portal a subscriber is handed to is minted by the provider for a customer it knows
        about, so an invented identifier gets as far as the button and no further: the control
        posts, the backend asks the provider, and the reader is told the portal could not be
        reached. With a sandbox key in ``demo/.env`` this creates a customer there, or reuses the
        one already created for that address, and the handoff can be followed all the way to the
        provider's own page.

        Without credentials it returns the invented identifier and the demo behaves exactly as a
        project that has not configured its backend, which is worth being able to look at too.

        Args:
            email: The person's email address.
            fallback: The invented identifier to use without credentials.

        Returns:
            The provider's customer identifier.
        """
        secret = getattr(settings, "DEV_ENV", {}).get("STRIPE_TEST_SECRET_KEY")
        if not secret:
            return fallback

        stripe.api_key = secret
        existing = stripe.Customer.list(email=email, limit=1).data
        if existing:
            return existing[0].id
        return stripe.Customer.create(email=email, name=email.partition("@")[0]).id

    def seed_offline_subscriptions(self, user_model):
        """Give the demo something for the user subscriptions page to show, without Stripe.

        ``regular.user`` gets two active subscriptions in different currencies, which is the
        several-at-once case. ``staff.user`` gets a trialing one. ``super.user`` is left with no
        customer at all, so the empty state is reachable without editing anything. A fourth,
        unlisted person gets a subscription of their own, which nothing this command creates
        for ``regular.user`` may ever show: the cross-user guarantee the page's own tests hold
        separately.

        The rows are written straight to the Stripe app's tables, which a real project never
        does (Article XI). The demo has no Stripe account to read them from.

        Args:
            user_model: The project's user model.
        """
        other_user, _ = user_model.objects.get_or_create(
            username="other.subscriber",
            defaults={"email": "other.subscriber@example.com"},
        )
        other_user.set_password(PASSWORD)
        other_user.save()

        self.invent_subscription(
            user_model.objects.get(username="regular.user"),
            "regular",
            "Basic",
            status="active",
            amount=2000,
            currency="usd",
        )
        self.invent_subscription(
            user_model.objects.get(username="regular.user"),
            "regular_premium",
            "Premium",
            status="active",
            amount=500000,
            currency="jpy",
        )
        self.invent_subscription(
            user_model.objects.get(username="staff.user"),
            "staff",
            "Basic",
            status="trialing",
            amount=2000,
            currency="usd",
        )
        self.invent_subscription(
            other_user,
            "other",
            "Basic",
            status="active",
            amount=2000,
            currency="usd",
        )

    def prime_catalogue(self, catalogue):
        """Put a Stripe-shaped catalogue in the cache, so the plans page works without Stripe.

        Basic, Pro and Team, each monthly and yearly. Basic monthly carries the identifier of
        the subscription ``regular.user`` is given, so that plan shows as theirs. It never
        expires: without a Stripe account there is nothing to read again, and the entry
        is removed by ``stripe_sync`` or by seeding against a sandbox.

        Args:
            catalogue: The Stripe app's catalogue.
        """
        products = [
            (
                "basic",
                "Basic",
                "For one person getting started.",
                ["One project", "Monthly usage report", "Email support"],
                2000,
                "price_demo_regular",
            ),
            (
                "pro",
                "Pro",
                "For people who use it every day.",
                [
                    "Up to ten projects",
                    "Weekly usage reports",
                    "Priority email support",
                    "Export to CSV and Excel",
                ],
                5000,
                None,
            ),
            (
                "team",
                "Team",
                "For a group working on the same projects, with one bill for everyone.",
                [
                    "Unlimited projects",
                    "Up to 25 team members, each with their own sign-in",
                    "Daily usage reports",
                    "Support by email and phone",
                    "Single sign-on",
                ],
                12000,
                None,
            ),
        ]
        prices = []
        for key, name, description, features, monthly, monthly_id in products:
            product = {
                "id": f"prod_demo_{key}",
                "object": "product",
                "active": True,
                "name": name,
                "description": description,
                "marketing_features": [{"name": feature} for feature in features],
            }
            for interval, amount, price_id in (
                ("month", monthly, monthly_id or f"price_demo_{key}_month"),
                ("year", monthly * 10, f"price_demo_{key}_year"),
            ):
                prices.append(
                    {
                        "id": price_id,
                        "object": "price",
                        "active": True,
                        "type": "recurring",
                        "billing_scheme": "per_unit",
                        "unit_amount": amount,
                        "currency": "usd",
                        "recurring": {
                            "interval": interval,
                            "interval_count": 1,
                            "usage_type": "licensed",
                        },
                        "product": product,
                    }
                )
        cache.set(catalogue.KEY, catalogue.order(prices), None)
        self.stdout.write("primed the plans page with a demo catalogue")

    def invent_subscription(self, user, key, product_name, **fields):
        """Record one invented subscription on the user's customer, creating the customer.

        Args:
            user: The person the subscription belongs to.
            key: Names the subscription, and so what its identifiers are.
            product_name: The name of the product it is for.
            **fields: The status, amount and currency of the subscription.
        """
        customer_model = apps.get_model("mvp_payments_stripe", "Customer")
        subscription_model = apps.get_model("mvp_payments_stripe", "Subscription")
        stripe_id = self.customer_id_for(user.email, f"cus_demo_{user.username}")
        customer, _ = customer_model.objects.update_or_create(
            user=user, defaults={"stripe_id": stripe_id}
        )
        now = timezone.now()
        subscription_model.objects.update_or_create(
            stripe_id=f"sub_demo_{key}",
            defaults={
                "customer": customer,
                "price_id": f"price_demo_{key}",
                "product_name": product_name,
                "interval": "month",
                "interval_count": 1,
                "current_period_start": now - timedelta(days=10),
                "current_period_end": now + timedelta(days=20),
                **fields,
            },
        )
