"""Every component this story adds renders standalone, from its attributes alone (T014).

No view runs to produce these — ``cotton_render`` builds a bare request and passes each
dataclass straight through as a component attribute, which is exactly the guarantee a project
overriding this page's template, or placing one of these components elsewhere, relies on.
"""

import re

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from mvp_payments.money import Money
from mvp_payments.namespaces.drf_stripe_records import (
    CurrentSubscription,
    Plan,
    PlanFeature,
)


class TestPricingTable:
    """``<c-drf-stripe.pricing-table>`` mounts the provider's own embed (T001, FR-011, SC-007).

    No amount, currency, billing frequency or plan name is produced by this component or
    anywhere else in this package — the provider renders every price inside its own frame.
    """

    def test_renders_the_providers_element_with_its_table_id_and_publishable_key(
        self, cotton_render
    ):
        html = cotton_render(
            "drf-stripe.pricing-table",
            table_id="prctbl_test123",
            publishable_key="pk_test_456",
        )

        assert "<stripe-pricing-table" in html
        assert 'pricing-table-id="prctbl_test123"' in html
        assert 'publishable-key="pk_test_456"' in html
        assert "<script" not in html
        assert not re.search(r"\d[\d,]*\.\d{2,3}", html)

    def test_carries_a_hidden_could_not_be_loaded_message_and_its_marker(
        self, cotton_render
    ):
        """The message is present in the markup and hidden, never absent, so
        revealing it needs no string from JavaScript (scenario 3, FR-010)."""
        html = cotton_render(
            "drf-stripe.pricing-table",
            table_id="prctbl_test123",
            publishable_key="pk_test_456",
        )

        assert "hidden data-mvp-payments-pricing-table-unavailable" in html
        assert "The plans could not be loaded. Try again later." in html

    def test_a_signed_in_person_with_an_address_carries_it_as_customer_email(
        self, cotton_render_string, rf, user
    ):
        user.email = "person@example.com"
        request = rf.get("/")
        request.user = user

        html = cotton_render_string(
            '<c-drf-stripe.pricing-table table_id="prctbl_test123" '
            'publishable_key="pk_test_456" />',
            context={"request": request},
        )

        assert 'customer-email="person@example.com"' in html

    def test_a_signed_in_person_with_no_address_carries_no_customer_email_attribute(
        self, cotton_render_string, rf, user
    ):
        request = rf.get("/")
        request.user = user

        html = cotton_render_string(
            '<c-drf-stripe.pricing-table table_id="prctbl_test123" '
            'publishable_key="pk_test_456" />',
            context={"request": request},
        )

        assert "customer-email" not in html
        assert 'pricing-table-id="prctbl_test123"' in html
        assert 'publishable-key="pk_test_456"' in html

    def test_an_anonymous_visitor_carries_no_customer_email_attribute(
        self, cotton_render_string, rf
    ):
        request = rf.get("/")
        request.user = AnonymousUser()

        html = cotton_render_string(
            '<c-drf-stripe.pricing-table table_id="prctbl_test123" '
            'publishable_key="pk_test_456" />',
            context={"request": request},
        )

        assert "customer-email" not in html

    def test_an_explicit_customer_email_wins_over_the_signed_in_persons_address(
        self, cotton_render_string, rf, user
    ):
        user.email = "person@example.com"
        request = rf.get("/")
        request.user = user

        html = cotton_render_string(
            '<c-drf-stripe.pricing-table table_id="prctbl_test123" '
            'publishable_key="pk_test_456" customer_email="explicit@example.com" />',
            context={"request": request},
        )

        assert 'customer-email="explicit@example.com"' in html
        assert "person@example.com" not in html

    def test_renders_completely_from_its_attributes_alone_for_an_anonymous_visitor(
        self, cotton_render_string, rf, django_assert_num_queries, db
    ):
        """No view, no context processor, no query — a page of the host project's own
        can place this component and give it nothing but its two attributes (T016,
        FR-001, FR-009, FR-011)."""
        request = rf.get("/")
        request.user = AnonymousUser()

        with django_assert_num_queries(0):
            html = cotton_render_string(
                "<article><h2>Order summary</h2>"
                '<c-drf-stripe.pricing-table table_id="prctbl_test123" '
                'publishable_key="pk_test_456" /></article>',
                context={"request": request},
            )

        assert "Order summary" in html
        assert "<stripe-pricing-table" in html
        assert 'pricing-table-id="prctbl_test123"' in html
        assert 'publishable-key="pk_test_456"' in html
        assert "customer-email" not in html


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


class TestPlansUnavailable:
    """``<c-drf-stripe.plans-unavailable>`` — plans cannot be shown yet, said
    plainly, on its own, given no attributes at all (T020, T022, FR-007)."""

    def test_renders_its_sentence_given_nothing(self, cotton_render):
        html = cotton_render("drf-stripe.plans-unavailable")

        assert "Plans not available" in html
        assert "This project has not configured its plans yet." in html


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
