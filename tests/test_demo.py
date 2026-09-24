"""The demo project, which is where the components get looked at as they land.

It is tested for the same reason ``test_app.py`` tests the template directory:
everything here fails quietly. A Cotton component that cannot be resolved
renders as empty output, a Tailwind class the packaged stylesheet does not emit
does nothing, and a navigation entry whose URL will not resolve is dropped from
the sidebar. None of that raises, so none of it shows up anywhere except in a
browser.
"""

import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse


class TestHomePage:
    """The page a reader lands on, and the shell it is drawn inside."""

    def test_page_is_served(self, client, db):
        assert client.get("/").status_code == 200

    def test_page_is_drawn_inside_the_application_shell(self, home_page):
        """The sidebar and the header, not a hand-rolled document.

        The breadcrumb trail is the header's, drawn from what the view
        declares, so its presence says the header is there and reading the page
        rather than merely that some markup rendered.
        """
        assert "<aside" in home_page
        assert 'aria-label="Main navigation"' in home_page
        assert 'aria-label="Breadcrumbs"' in home_page
        assert '<span class="mvp-breadcrumb-text">Home</span>' in home_page

    def test_title_names_the_page_and_the_site(self, home_page):
        """The site half comes from CurrentSiteMiddleware and the named row.

        Without either the title still renders, just with nothing after the
        separator, which is why the whole string is pinned rather than the page
        name alone.
        """
        title = re.search(r"<title>(.*?)</title>", home_page, re.S).group(1)
        assert " ".join(title.split()) == "Home | django-mvp-payments"

    def test_page_heading_is_the_page_title(self, home_page):
        assert re.search(r"<h1[^>]*>\s*Home\s*</h1>", home_page)

    def test_page_says_what_the_package_is(self, home_page):
        """The one thing the page exists to do."""
        assert "&lt;c-drf-stripe.plan-grid&gt;" in home_page
        assert "drf-stripe-subscription" in home_page

    def test_the_pricing_table_is_present_with_the_demos_values_for_an_anonymous_visitor(
        self, home_page
    ):
        """A visitor who has not signed in reaches the same component the Account
        Center's Plans page renders, given the demo's own values as attributes
        directly rather than through a view or a context processor (T017, T018,
        FR-001, FR-009, FR-011)."""
        assert "<stripe-pricing-table" in home_page
        assert 'pricing-table-id="prctbl_not_a_real_table"' in home_page
        assert 'publishable-key="pk_test_not_a_real_key"' in home_page

    def test_the_copy_names_it_as_the_same_component_the_account_center_renders(
        self, home_page
    ):
        """The claim the placement is making, not three words that co-occur.

        ``"same"`` and ``"Account Center"`` both appear elsewhere on this page,
        so asserting them separately passed whether or not the sentence saying
        what this section is survived an edit. Whitespace is collapsed first
        because the sentence wraps across source lines, and where it wraps is
        not something a test should hold still.
        """
        collapsed = re.sub(r"\s+", " ", home_page)

        assert "The same component, on a page of the project&#x27;s own" in collapsed
        assert "component the Account Center's Plans page renders" in collapsed

    def test_both_ways_of_building_a_page_are_presented_as_equals(self, home_page):
        """G2, and the grid of cards that carries it.

        Cotton renders a component it cannot resolve as empty output, so a
        broken ``c-grid`` or ``c-card`` would take this section off the page
        without raising. Pinning the card markup alongside the sentence is what
        tells a missing component apart from an edit to the prose.
        """
        assert home_page.count("card-title") == 2
        assert "Native" in home_page
        assert "Provider embed" in home_page
        assert "Neither is the fallback for the other." in home_page


class TestUnavailableStateRoutes:
    """The two routes that make US-4's states reachable by clicking.

    Both belong to the demo, not the package. They are tested here because the
    states they show are the ones nobody sees during ordinary use — a project
    that has configured everything correctly never reaches either — so a route
    that quietly stopped rendering them would go unnoticed indefinitely.
    """

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
        """The point of that page, and the one way it can silently stop making it.

        Emptying ``provider_library`` is how the page shows a mount point the
        provider's library never came to life for. ``pricing_table.js`` is ours
        and does the revealing, so it has to survive that emptying — if it ever
        moves back inside the block, this page renders a hidden message with
        nothing left to reveal it and looks identical to a working one.
        """
        content = client.get("/no-library/").content.decode()

        assert "js.stripe.com" not in content
        assert "pricing_table.js" in content

    def test_both_routes_are_reachable_from_the_landing_page(self, home_page):
        assert "/plans-unconfigured/" in home_page
        assert "/no-library/" in home_page


class TestSidebarMenu:
    """What the navigation holds while no component exists."""

    def test_the_home_page_is_linked(self, sidebar_navigation):
        assert "<span>Home</span>" in sidebar_navigation
        assert 'href="/"' in sidebar_navigation

    def test_that_is_the_only_entry(self, sidebar_navigation):
        """No component pages exist, so nothing else belongs in the sidebar yet."""
        assert sidebar_navigation.count("<li") == 1

    def test_every_entry_leads_somewhere(self, home_page):
        """A navigation node with no resolving target is a dead control.

        django-mvp draws a node from its leaf template until it has children,
        so a section declared before it holds a page reaches the browser as a
        button carrying the literal text ``href="None"`` — inert, and not
        distinguishable from a working entry by eye.
        """
        assert 'href="None"' not in home_page


class TestThemeSwitching:
    """A component is meant to follow the site's theme rather than fix colours.

    The demo offers several themes so that claim can be looked at, which only
    works if the layout configuration reaches the page. It does so through a
    context processor that is easy to leave out of a settings file, and leaving
    it out costs no error — every configured option simply resolves to nothing.
    """

    def test_every_configured_theme_is_offered_by_the_control(self, home_page):
        for theme in ("light", "dark", "corporate", "dracula"):
            assert f'data-set-theme="{theme}"' in home_page

    def test_the_sidebar_carries_the_configured_title(self, home_page):
        """The other half of the same configuration, read by a different template."""
        assert re.search(
            r'<span class="mvp-sidebar-title[^"]*">django-mvp-payments</span>',
            home_page,
        )


@pytest.mark.django_db
class TestSeedDemoCommand:
    """The demo's subscription data, so the subscription page has something to show
    (T003) without a developer editing anything by hand.
    """

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
class TestBillingPortalHandoff:
    """The demo's own way through to the provider's hosted portal.

    It exists because the backend's equivalent raises for anybody who has used it before, so
    what matters here is not that one call works but that the second one does. These never
    reach the provider: the session is a network call, and the thing under test is which
    customer it is asked for and what comes back to the page.
    """

    ENDPOINT = "/api/billing-portal/"

    @pytest.fixture
    def subscriber(self, client):
        """Somebody the backend holds a customer record for, signed in."""
        user = get_user_model().objects.create_user(
            username="subscriber", password="password"
        )
        apps.get_model("drf_stripe", "StripeUser").objects.create(
            user=user, customer_id="cus_a_real_looking_one"
        )
        client.force_login(user)
        return user

    def test_a_subscriber_is_given_the_address_the_provider_minted(
        self, client, subscriber
    ):
        with patch(
            "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create",
            return_value=SimpleNamespace(url="https://billing.example.com/session"),
        ):
            response = client.post(self.ENDPOINT)

        assert response.status_code == 200
        assert response.json() == {"url": "https://billing.example.com/session"}

    def test_it_keeps_working_on_every_call_after_the_first(self, client, subscriber):
        """The defect this endpoint stands in for, asserted directly.

        The backend's own endpoint succeeds exactly once per person and raises an integrity
        error after that, because it looks its customer record up by an identifier it filled
        in on the first call. A single-call test would pass against that too.
        """
        with patch(
            "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create",
            return_value=SimpleNamespace(url="https://billing.example.com/session"),
        ):
            statuses = [client.post(self.ENDPOINT).status_code for _ in range(3)]

        assert statuses == [200, 200, 200]

    def test_the_provider_is_asked_for_this_persons_own_customer(
        self, client, subscriber
    ):
        """Whose portal it is, which is the one thing a mistake here would leak."""
        with patch(
            "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create",
            return_value=SimpleNamespace(url="https://billing.example.com/session"),
        ) as create:
            client.post(self.ENDPOINT)

        assert create.call_args.kwargs["customer"] == "cus_a_real_looking_one"

    def test_the_reader_is_sent_back_through_the_refresh(self, client, subscriber):
        """The backend's default return address is a frontend on another port.

        A wrong one strands somebody on the provider's site with no way back that leads here.
        The way back refreshes the backend's records first, so a change made in the portal
        shows on arrival.
        """
        with patch(
            "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create",
            return_value=SimpleNamespace(url="https://billing.example.com/session"),
        ) as create:
            client.post(self.ENDPOINT)

        assert create.call_args.kwargs["return_url"].endswith(reverse("billing-return"))
        assert "flow_data" not in create.call_args.kwargs

    def test_somebody_with_no_customer_record_gets_no_portal(self, client):
        """And no customer is created for them by their asking (D7).

        The control is already absent for this person, so arriving here means a stale page or
        a direct post. Creating a customer for whoever asks is the backend behaviour that
        earned the suppression in the first place.
        """
        user = get_user_model().objects.create_user(
            username="nobody", password="password"
        )
        client.force_login(user)

        with patch(
            "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create"
        ) as create:
            response = client.post(self.ENDPOINT)

        assert response.status_code == 409
        create.assert_not_called()

    def test_signing_in_is_required(self, client):
        with patch(
            "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create"
        ) as create:
            response = client.post(self.ENDPOINT)

        assert response.status_code == 302
        create.assert_not_called()


@pytest.mark.django_db
class TestPlanSwitchHandoff:
    """The demo's way to the provider's plan-change screen, behind "Switch plans"."""

    ENDPOINT = "/api/plan-switch/"
    CREATE = "drf_stripe.stripe_api.api.stripe_api.billing_portal.Session.create"

    def test_it_opens_the_plan_change_screen_for_the_persons_current_subscription(
        self, subscriber_client, current_subscription, stripe_user
    ):
        with patch(
            self.CREATE,
            return_value=SimpleNamespace(url="https://billing.example.com/flow"),
        ) as create:
            response = subscriber_client.post(self.ENDPOINT)

        assert response.status_code == 200
        assert response.json() == {"url": "https://billing.example.com/flow"}
        kwargs = create.call_args.kwargs
        assert kwargs["customer"] == stripe_user.customer_id
        flow = kwargs["flow_data"]
        assert flow["type"] == "subscription_update"
        assert (
            flow["subscription_update"]["subscription"]
            == current_subscription.subscription_id
        )
        assert flow["after_completion"]["redirect"]["return_url"].endswith(
            reverse("billing-return")
        )

    def test_somebody_with_nothing_current_has_nothing_to_switch(
        self, logged_in_client, stripe_user
    ):
        with patch(self.CREATE) as create:
            response = logged_in_client.post(self.ENDPOINT)

        assert response.status_code == 409
        create.assert_not_called()

    def test_signing_in_is_required(self, client, db):
        with patch(self.CREATE) as create:
            response = client.post(self.ENDPOINT)

        assert response.status_code == 302
        create.assert_not_called()


@pytest.mark.django_db
class TestBillingReturn:
    """Where the provider sends a reader back to: refresh, then the subscription page."""

    SYNC = "drf_stripe.stripe_api.subscriptions.stripe_api_update_subscriptions"

    def test_it_refreshes_from_the_provider_then_shows_the_subscription_page(
        self, logged_in_client
    ):
        with patch(self.SYNC) as sync:
            response = logged_in_client.get(reverse("billing-return"))

        sync.assert_called_once_with(status="all", ignore_new_user_creation_errors=True)
        assert response.status_code == 302
        assert response.url == reverse("payments:drf-stripe-subscription")

    def test_signing_in_is_required(self, client, db):
        with patch(self.SYNC) as sync:
            response = client.get(reverse("billing-return"))

        assert response.status_code == 302
        sync.assert_not_called()


@pytest.mark.django_db
class TestSeedDemoAgainstTheSandbox:
    """With a sandbox key in ``demo/.env``, subscriptions are made at the provider.

    The provider is never reached here. What is under test is who gets a subscription, that
    nobody gets a second one, and that invented records never sit beside real ones.
    """

    @pytest.fixture
    def sandbox(self, settings):
        settings.DEV_ENV = {"STRIPE_TEST_SECRET_KEY": "sk_test_sandbox"}
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
        StripeUser = apps.get_model("drf_stripe", "StripeUser")
        stripe_user = StripeUser.objects.create(
            user=get_user_model().objects.create_user(username="leftover"),
            customer_id="cus_leftover",
        )
        Subscription.objects.create(
            subscription_id="sub_demo_regular",
            stripe_user=stripe_user,
            status="active",
            cancel_at_period_end=False,
        )

        call_command("seed_demo")

        assert not Subscription.objects.filter(
            subscription_id__startswith="sub_demo_"
        ).exists()

    def test_the_backends_own_synchronisation_reads_everything_back(self, sandbox):
        call_command("seed_demo")

        sandbox.pull_products.assert_called_once_with()
        sandbox.pull_subscriptions.assert_called_once_with(
            status="all", ignore_new_user_creation_errors=True
        )
