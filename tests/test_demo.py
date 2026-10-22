"""The demo project, which is where the components get looked at as they land.

It is tested for the same reason ``test_app.py`` tests the template directory:
everything here fails quietly. A Cotton component that cannot be resolved
renders as empty output, a Tailwind class the packaged stylesheet does not emit
does nothing, and a navigation entry whose URL will not resolve is dropped from
the sidebar. None of that raises, so none of it shows up anywhere except in a
browser.
"""

import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command

from mvp_payments.stripe.models import Customer as StripeCustomer
from tests.factories import SubscriptionFactory
from tests.stripe_fake import customer_payload

SANDBOX_SUBSCRIBER_NAMES = ("regular.user", "staff.user", "other.subscriber")


class TestHomePage:
    def test_page_is_served(self, client, db):
        assert client.get("/").status_code == 200

    def test_page_is_drawn_inside_the_application_shell(self, home_page):
        assert "<aside" in home_page
        assert 'aria-label="Main navigation"' in home_page
        assert 'aria-label="Breadcrumbs"' in home_page
        assert '<span aria-current="page">Home</span>' in home_page

    def test_title_names_the_page_and_the_site(self, home_page):
        title = re.search(r"<title>(.*?)</title>", home_page, re.S).group(1)
        assert " ".join(title.split()) == "Home | django-mvp-payments"

    def test_the_pricing_table_is_present_with_the_demos_values_for_an_anonymous_visitor(
        self, home_page
    ):
        assert "<stripe-pricing-table" in home_page
        assert 'pricing-table-id="prctbl_not_a_real_table"' in home_page
        assert 'publishable-key="pk_test_not_a_real_key"' in home_page


class TestUnavailableStateRoutes:
    def test_the_unconfigured_route_states_plans_are_unavailable(self, client, db):
        content = client.get("/plans-unconfigured/").content.decode()

        assert "<stripe-pricing-table" not in content

    def test_the_no_library_route_emits_the_mount_point(self, client, db):
        content = client.get("/no-library/").content.decode()

        assert "<stripe-pricing-table" in content
        assert 'pricing-table-id="prctbl_not_a_real_table"' in content

    def test_the_no_library_route_drops_the_provider_library_and_keeps_ours(
        self, client, db
    ):
        content = client.get("/no-library/").content.decode()

        assert "js.stripe.com" not in content
        assert "pricing_table.js" in content

    def test_both_routes_are_reachable_from_the_landing_page(self, home_page):
        assert "/plans-unconfigured/" in home_page
        assert "/no-library/" in home_page


class TestDemoStripeSetup:
    def test_the_global_api_version_is_the_one_drf_stripe_was_written_against(
        self, monkeypatch
    ):
        import stripe

        monkeypatch.setattr(stripe, "api_version", "2026-09-30.endive")

        apps.get_app_config("demo").ready()

        assert stripe.api_version == "2020-08-27"

    def test_the_demo_does_not_mount_the_backends_url_configuration(self, db):
        from django.urls import Resolver404, resolve

        with pytest.raises(Resolver404):
            resolve("/api/stripe/customer-portal/")


def load_demo_settings():
    """Run demo/settings.py afresh, so the environment it reads is the one the test set."""
    spec = importlib.util.spec_from_file_location(
        "demo_settings_probe", "demo/settings.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDemoWebhookSecret:
    def test_the_secret_stripe_listen_prints_is_taken_from_the_environment(
        self, monkeypatch
    ):
        monkeypatch.setenv("STRIPE_TEST_WEBHOOK_SECRET", "whsec_from_stripe_listen")

        settings = load_demo_settings()

        assert (
            settings.MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"] == "whsec_from_stripe_listen"
        )

    def test_without_one_the_demo_still_has_a_value_so_it_runs(self, monkeypatch):
        monkeypatch.delenv("STRIPE_TEST_WEBHOOK_SECRET", raising=False)
        monkeypatch.setattr(Path, "exists", lambda self: False)

        settings = load_demo_settings()

        assert settings.MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"]


class TestSidebarMenu:
    def test_the_home_page_is_linked(self, sidebar_navigation):
        assert 'href="/"' in sidebar_navigation

    def test_every_entry_leads_somewhere(self, home_page):
        assert 'href="None"' not in home_page


class TestThemeSwitching:
    def test_every_configured_theme_is_offered_by_the_control(self, home_page):
        for theme in ("light", "dark", "corporate", "dracula"):
            assert f'data-set-theme="{theme}"' in home_page

    def test_the_sidebar_carries_the_configured_title(self, home_page):
        assert re.search(
            r'<span class="mvp-sidebar-title[^"]*">django-mvp-payments</span>',
            home_page,
        )


@pytest.mark.django_db
class TestSeedDemoCommand:
    def _stripe_user_for(self, username):
        StripeUser = apps.get_model("drf_stripe", "StripeUser")
        user = get_user_model().objects.get(username=username)
        return StripeUser.objects.get(pk=user.pk)

    def test_regular_user_holds_a_subscription_with_two_priced_items_in_different_currencies(
        self,
    ):
        call_command("seed_demo")

        stripe_user = self._stripe_user_for("regular.user")
        items = list(stripe_user.current_subscription_items.select_related("price"))
        assert len(items) == 2
        currencies = {item.price.currency for item in items}
        assert len(currencies) == 2

    def test_regular_users_products_carry_features(self):
        call_command("seed_demo")

        stripe_user = self._stripe_user_for("regular.user")
        for item in stripe_user.current_subscription_items.select_related(
            "price__product"
        ):
            assert item.price.product.linked_features.exists()

    def test_staff_user_holds_a_trialing_subscription(self):
        call_command("seed_demo")

        stripe_user = self._stripe_user_for("staff.user")
        assert list(stripe_user.subscriptions.values_list("status", flat=True)) == [
            "trialing"
        ]

    def test_super_user_holds_no_subscription(self):
        call_command("seed_demo")

        StripeUser = apps.get_model("drf_stripe", "StripeUser")
        user = get_user_model().objects.get(username="super.user")
        assert not StripeUser.objects.filter(pk=user.pk).exists()

    def test_running_it_twice_leaves_exactly_one_of_each_record(self):
        call_command("seed_demo")
        call_command("seed_demo")

        StripeUser = apps.get_model("drf_stripe", "StripeUser")
        Subscription = apps.get_model("drf_stripe", "Subscription")
        assert get_user_model().objects.filter(username="regular.user").count() == 1
        assert StripeUser.objects.count() == StripeUser.objects.distinct().count()
        stripe_user = self._stripe_user_for("regular.user")
        assert Subscription.objects.filter(stripe_user=stripe_user).count() == 1


@pytest.mark.django_db
class TestSeedDemoAgainstTheSandbox:
    @pytest.fixture
    def sandbox(self, settings, stripe_fake):
        settings.DEV_ENV = {"STRIPE_TEST_SECRET_KEY": "sk_test_sandbox"}
        for name in SANDBOX_SUBSCRIBER_NAMES:
            stripe_fake.respond(
                "GET", f"/v1/customers/cus_{name}", customer_payload(f"cus_{name}")
            )
        stripe_fake.respond_with_list("/v1/subscriptions", [])
        stripe_module = "demo.management.commands.seed_demo.stripe"
        with (
            patch(f"{stripe_module}.Customer") as customer,
            patch(f"{stripe_module}.Price") as price,
            patch(f"{stripe_module}.Subscription") as subscription,
            patch(f"{stripe_module}.PaymentMethod") as payment_method,
            patch(
                "drf_stripe.stripe_api.products.stripe_api_update_products_prices"
            ) as pull_products,
            patch(
                "drf_stripe.stripe_api.subscriptions.stripe_api_update_subscriptions"
            ) as pull_subscriptions,
        ):
            customer.list.return_value = SimpleNamespace(data=[])
            customer.create.side_effect = lambda email, name: SimpleNamespace(
                id=f"cus_{name}"
            )
            price.list.return_value = SimpleNamespace(
                data=[
                    self._price("price_yearly", 3600, "year"),
                    self._price("price_dear", 999, "month"),
                    self._price("price_cheap", 399, "month"),
                ]
            )
            subscription.list.return_value = SimpleNamespace(data=[])
            payment_method.attach.return_value = SimpleNamespace(id="pm_visa")
            yield SimpleNamespace(
                subscription=subscription,
                pull_products=pull_products,
                pull_subscriptions=pull_subscriptions,
            )

    @staticmethod
    def _price(price_id, amount, interval):
        return SimpleNamespace(
            id=price_id,
            unit_amount=amount,
            recurring=SimpleNamespace(interval=interval, interval_count=1),
        )

    def test_each_subscriber_gets_one_on_the_cheapest_monthly_price(self, sandbox):
        call_command("seed_demo")

        created = {
            call.kwargs["customer"]: call.kwargs
            for call in sandbox.subscription.create.call_args_list
        }
        assert set(created) == {
            "cus_regular.user",
            "cus_staff.user",
            "cus_other.subscriber",
        }
        for kwargs in created.values():
            assert kwargs["items"] == [{"price": "price_cheap"}]
        assert created["cus_staff.user"]["trial_period_days"] == 14
        assert "trial_period_days" not in created["cus_regular.user"]

    def test_somebody_already_subscribed_is_not_given_a_second(self, sandbox):
        sandbox.subscription.list.return_value = SimpleNamespace(
            data=[SimpleNamespace(status="active")]
        )

        call_command("seed_demo")

        sandbox.subscription.create.assert_not_called()

    def test_super_user_is_left_with_nothing(self, sandbox):
        call_command("seed_demo")

        StripeUser = apps.get_model("drf_stripe", "StripeUser")
        user = get_user_model().objects.get(username="super.user")
        assert not StripeUser.objects.filter(pk=user.pk).exists()

    def test_invented_subscriptions_from_an_offline_run_are_removed(self, sandbox):
        Subscription = apps.get_model("drf_stripe", "Subscription")
        SubscriptionFactory(subscription_id="sub_demo_regular")

        call_command("seed_demo")

        assert not Subscription.objects.filter(
            subscription_id__startswith="sub_demo_"
        ).exists()

    def test_each_subscriber_is_recorded_by_the_stripe_app_from_the_sandbox(
        self, sandbox, stripe_fake
    ):
        call_command("seed_demo")

        recorded = dict(
            StripeCustomer.objects.values_list("user__username", "stripe_id")
        )
        assert recorded == {
            "regular.user": "cus_regular.user",
            "staff.user": "cus_staff.user",
            "other.subscriber": "cus_other.subscriber",
        }
        assert "/v1/customers/cus_regular.user" in stripe_fake.paths("GET")

    def test_the_backends_own_synchronisation_reads_everything_back(self, sandbox):
        call_command("seed_demo")

        sandbox.pull_products.assert_called_once_with()
        sandbox.pull_subscriptions.assert_called_once_with(
            status="all", ignore_new_user_creation_errors=True
        )
