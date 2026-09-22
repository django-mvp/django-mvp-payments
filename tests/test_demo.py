"""The demo project, which is where the components get looked at as they land.

It is tested for the same reason ``test_app.py`` tests the template directory:
everything here fails quietly. A Cotton component that cannot be resolved
renders as empty output, a Tailwind class the packaged stylesheet does not emit
does nothing, and a navigation entry whose URL will not resolve is dropped from
the sidebar. None of that raises, so none of it shows up anywhere except in a
browser.
"""

import re

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command


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
        assert "same" in home_page
        assert "Account Center" in home_page
        assert "Plans page" in home_page

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
