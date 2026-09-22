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


class TestPlansLink:
    """``<c-drf-stripe.plans-link>`` — the way to the plans page.

    That page left the Account Center's navigation, so this control is how a
    person reaches it.
    """

    def test_a_subscriber_is_offered_a_switch(self, cotton_render):
        html = cotton_render(
            "drf-stripe.plans-link", url="/payments/drf-stripe/plans/", subscribed=True
        )

        assert 'href="/payments/drf-stripe/plans/"' in html
        assert "Switch plans" in html
        assert "Choose a plan" not in html

    def test_somebody_on_no_plan_is_offered_a_choice(self, cotton_render):
        """ "Switch plans" reads as a mistake to a person who is not on one."""
        html = cotton_render(
            "drf-stripe.plans-link", url="/payments/drf-stripe/plans/", subscribed=False
        )

        assert 'href="/payments/drf-stripe/plans/"' in html
        assert "Choose a plan" in html
        assert "Switch plans" not in html

    def test_given_no_address_it_renders_nothing_at_all(self, cotton_render):
        """A control leading nowhere is worse than no control (Article XVI)."""
        html = cotton_render("drf-stripe.plans-link", url=None)

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
        assert "Manage subscription" in html
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


class TestStandalone:
    """Every component this feature added, placed inside a template that has nothing to do
    with the shipped page, given only its attributes (T029, FR-012, SC-006).

    ``cotton_render`` above proves each component renders in isolation; this gathers the
    single guarantee SC-006 names by placing the same tags inside markup of a template's own
    that no view of this package's ever produces, confirming nothing here depends on being
    reached through ``SubscriptionPageView``.
    """

    def test_amount_renders_inside_an_unrelated_template(self, cotton_render_string):
        html = cotton_render_string(
            '<article><h2>Order summary</h2><c-drf-stripe.amount :amount="amount" /></article>',
            context={"amount": Money(minor_units=2000, currency="USD")},
        )

        assert "Order summary" in html
        assert "20.00 USD" in html

    def test_plan_renders_inside_an_unrelated_template(self, cotton_render_string):
        plan = Plan(
            name="Premium monthly",
            amount=Money(minor_units=2500, currency="USD"),
            frequency="month_1",
            quantity=1,
        )

        html = cotton_render_string(
            '<section><h1>Pricing</h1><c-drf-stripe.plan :plan="plan" /></section>',
            context={"plan": plan},
        )

        assert "Pricing" in html
        assert "Premium monthly" in html
        assert "25.00 USD" in html

    def test_subscription_renders_inside_an_unrelated_template(
        self, cotton_render_string
    ):
        subscription = CurrentSubscription(
            status="active", period_start=None, period_end=None, plans=()
        )

        html = cotton_render_string(
            "<aside><h3>Dashboard widget</h3>"
            '<c-drf-stripe.subscription :subscription="subscription" /></aside>',
            context={"subscription": subscription},
        )

        assert "Dashboard widget" in html
        assert "active" in html

    def test_features_renders_inside_an_unrelated_template(self, cotton_render_string):
        features = (PlanFeature(identifier="reports", description="Advanced reports"),)

        html = cotton_render_string(
            "<footer><p>What's included</p>"
            '<c-drf-stripe.features :features="features" /></footer>',
            context={"features": features},
        )

        assert "What's included" in html
        assert "Advanced reports" in html

    def test_portal_link_renders_inside_an_unrelated_template(
        self, cotton_render_string
    ):
        """Its markup comes from its attribute; its CSRF token does not.

        Every other component here renders completely from what it is given. This one
        also reads ``{{ csrf_token }}``, which Django's own context processor supplies,
        so a render with no request behind it produces the control with an empty token.
        That is the same dependency every CSRF-protected form in Django has, and making
        a caller pass the token instead would invite them to pass a stale one — so it is
        declared rather than removed, here and in the component and the documentation.
        ``TestSubscriptionPage.test_the_portal_control_carries_a_usable_csrf_token``
        proves it is populated when a request renders the page.
        """
        html = cotton_render_string(
            '<nav><span>Account</span><c-drf-stripe.portal-link :endpoint="endpoint" /></nav>',
            context={"endpoint": "/api/stripe/customer-portal/"},
        )

        assert "Account" in html
        assert 'data-endpoint="/api/stripe/customer-portal/"' in html
        assert 'data-csrf-token=""' in html

    def test_no_subscription_renders_inside_an_unrelated_template(
        self, cotton_render_string
    ):
        html = cotton_render_string(
            "<main><h1>Welcome</h1><c-drf-stripe.no-subscription /></main>"
        )

        assert "Welcome" in html
        assert "No current subscription" in html
