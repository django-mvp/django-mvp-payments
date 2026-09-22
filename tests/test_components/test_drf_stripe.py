"""Every component this story adds renders standalone, from its attributes alone (T014).

No view runs to produce these — ``cotton_render`` builds a bare request and passes each
dataclass straight through as a component attribute, which is exactly the guarantee a project
overriding this page's template, or placing one of these components elsewhere, relies on.
"""

import re

from django.utils import timezone

from mvp_payments.money import Money
from mvp_payments.namespaces.drf_stripe_records import (
    CurrentSubscription,
    Plan,
    PlanFeature,
)


class TestAmount:
    """``<c-drf-stripe.amount>`` renders the ``Money`` it was given."""

    def test_renders_the_amount_it_was_given(self, cotton_render):
        html = cotton_render(
            "drf-stripe.amount", amount=Money(minor_units=2000, currency="USD")
        )

        assert "20.00 USD" in html

    def test_a_currencyless_amount_renders_nothing_for_the_figure(self, cotton_render):
        html = cotton_render(
            "drf-stripe.amount", amount=Money(minor_units=2000, currency="")
        )

        assert "2000" not in html
        assert "20.00" not in html


class TestPlan:
    """``<c-drf-stripe.plan>`` renders one priced item's name, amount, frequency and quantity."""

    def test_renders_the_name_amount_and_frequency_it_was_given(self, cotton_render):
        plan = Plan(
            name="Premium monthly",
            amount=Money(minor_units=2500, currency="USD"),
            frequency="month_1",
            quantity=1,
        )

        html = cotton_render("drf-stripe.plan", plan=plan)

        assert "Premium monthly" in html
        assert "25.00 USD" in html
        assert "every month" in html

    def test_a_quantity_above_one_is_shown(self, cotton_render):
        plan = Plan(
            name="Seats",
            amount=Money(minor_units=500, currency="USD"),
            frequency="month_1",
            quantity=3,
        )

        html = cotton_render("drf-stripe.plan", plan=plan)

        assert "3" in html

    def test_an_unrecognised_frequency_renders_as_itself(self, cotton_render):
        plan = Plan(
            name="Odd billing",
            amount=Money(minor_units=500, currency="USD"),
            frequency="fortnight_1",
            quantity=1,
        )

        html = cotton_render("drf-stripe.plan", plan=plan)

        assert "fortnight_1" in html

    def test_its_features_render_beneath_it(self, cotton_render):
        plan = Plan(
            name="Premium monthly",
            amount=Money(minor_units=2500, currency="USD"),
            frequency="month_1",
            quantity=1,
            features=(
                PlanFeature(identifier="reports", description="Advanced reports"),
            ),
        )

        html = cotton_render("drf-stripe.plan", plan=plan)

        assert "Advanced reports" in html

    def test_no_features_renders_no_heading_or_list(self, cotton_render):
        plan = Plan(
            name="Basic",
            amount=Money(minor_units=500, currency="USD"),
            frequency="month_1",
            quantity=1,
        )

        html = cotton_render("drf-stripe.plan", plan=plan)

        assert "<ul" not in html
        assert "<li" not in html


class TestSubscription:
    """``<c-drf-stripe.subscription>`` renders one ``CurrentSubscription`` as a card."""

    def test_renders_the_status_and_its_plans(self, cotton_render):
        plan = Plan(
            name="Premium monthly",
            amount=Money(minor_units=2500, currency="USD"),
            frequency="month_1",
            quantity=1,
        )
        subscription = CurrentSubscription(
            status="active",
            period_start=None,
            period_end=None,
            plans=(plan,),
        )

        html = cotton_render("drf-stripe.subscription", subscription=subscription)

        assert "active" in html
        assert "Premium monthly" in html

    def test_renders_a_recorded_period(self, cotton_render):
        now = timezone.now()
        subscription = CurrentSubscription(
            status="active", period_start=now, period_end=now, plans=()
        )

        html = cotton_render("drf-stripe.subscription", subscription=subscription)

        assert str(now.year) in html

    def test_an_unrecognised_status_renders_as_itself_with_no_special_variant(
        self, cotton_render
    ):
        subscription = CurrentSubscription(
            status="paused", period_start=None, period_end=None, plans=()
        )

        html = cotton_render("drf-stripe.subscription", subscription=subscription)

        assert "paused" in html
        assert "badge-success" not in html
        assert "badge-info" not in html
        assert "badge-warning" not in html


class TestFeatures:
    """``<c-drf-stripe.features>`` lists what a plan's product grants inside the
    application (FR-009)."""

    def test_lists_the_features_it_is_given(self, cotton_render):
        features = (
            PlanFeature(identifier="reports", description="Advanced reports"),
            PlanFeature(identifier="seats", description="Unlimited seats"),
        )

        html = cotton_render("drf-stripe.features", features=features)

        assert "Advanced reports" in html
        assert "Unlimited seats" in html

    def test_shows_the_identifier_where_there_is_no_description(self, cotton_render):
        features = (PlanFeature(identifier="priority_support", description=""),)

        html = cotton_render("drf-stripe.features", features=features)

        assert "priority_support" in html

    def test_renders_nothing_at_all_when_given_none(self, cotton_render):
        """Nothing at all, heading included — an empty section is worse than no section."""
        html = cotton_render("drf-stripe.features", features=())

        assert html.strip() == ""


class TestPortalLink:
    """``<c-drf-stripe.portal-link>`` — the way through to the provider's billing
    portal (T016, D3, D5)."""

    def test_given_an_endpoint_it_renders_a_control_carrying_it_and_a_csrf_token(
        self, cotton_render
    ):
        html = cotton_render(
            "drf-stripe.portal-link", endpoint="/api/stripe/customer-portal/"
        )

        assert 'data-endpoint="/api/stripe/customer-portal/"' in html
        assert re.search(r'data-csrf-token="[^"]+"', html)
        assert "<button" in html
        assert "Manage billing" in html
        assert re.search(r'aria-describedby="([\w-]+)"', html)
        note_id = re.search(r'aria-describedby="([\w-]+)"', html).group(1)
        assert f'id="{note_id}"' in html
        assert "provider" in html.lower()
        assert "hidden data-mvp-payments-portal-link-failure" in html

    def test_given_no_endpoint_it_states_the_provider_manages_it_and_renders_no_control(
        self, cotton_render
    ):
        html = cotton_render("drf-stripe.portal-link", endpoint=None)

        assert "<button" not in html
        assert "provider" in html.lower()
        assert "cannot be reached" in html.lower()


class TestNoSubscription:
    """``<c-drf-stripe.no-subscription>`` — nothing current to show, on its own,
    given no attributes at all (T026, D11)."""

    def test_renders_its_heading_and_message_given_nothing(self, cotton_render):
        html = cotton_render("drf-stripe.no-subscription")

        assert "No current subscription" in html
        assert "You have no subscription that is currently active." in html
