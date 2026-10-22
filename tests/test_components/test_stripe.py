"""Every component renders standalone, from its attributes alone.

No view runs to produce these — ``cotton_render`` builds a bare request and passes each
dataclass straight through as a component attribute, which is exactly the guarantee a project
overriding this page's template, or placing one of these components elsewhere, relies on.
"""

import re

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from mvp_payments.money import Money
from mvp_payments.namespaces.stripe_records import CurrentSubscription


class TestPricingTable:
    def test_renders_the_providers_element_with_its_table_id_and_publishable_key(
        self, cotton_render
    ):
        html = cotton_render(
            "stripe.pricing-table",
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
        html = cotton_render(
            "stripe.pricing-table",
            table_id="prctbl_test123",
            publishable_key="pk_test_456",
        )

        assert "hidden data-mvp-payments-pricing-table-unavailable" in html

    def test_a_signed_in_person_with_an_address_carries_it_as_customer_email(
        self, cotton_render_string, rf, user
    ):
        user.email = "person@example.com"
        request = rf.get("/")
        request.user = user

        html = cotton_render_string(
            '<c-stripe.pricing-table table_id="prctbl_test123" '
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
            '<c-stripe.pricing-table table_id="prctbl_test123" '
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
            '<c-stripe.pricing-table table_id="prctbl_test123" '
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
            '<c-stripe.pricing-table table_id="prctbl_test123" '
            'publishable_key="pk_test_456" customer_email="explicit@example.com" />',
            context={"request": request},
        )

        assert 'customer-email="explicit@example.com"' in html
        assert "person@example.com" not in html

    def test_a_reference_is_carried_as_the_client_reference_id(self, cotton_render):
        html = cotton_render(
            "stripe.pricing-table",
            table_id="prctbl_test123",
            publishable_key="pk_test_456",
            client_reference_id="7_abc123",
        )

        assert 'client-reference-id="7_abc123"' in html

    def test_no_reference_carries_no_client_reference_id_attribute(self, cotton_render):
        html = cotton_render(
            "stripe.pricing-table",
            table_id="prctbl_test123",
            publishable_key="pk_test_456",
        )

        assert "client-reference-id" not in html
        assert "customer-session-client-secret" not in html

    def test_a_customer_session_is_carried_and_replaces_the_customer_email(
        self, cotton_render_string, rf, user
    ):
        user.email = "person@example.com"
        request = rf.get("/")
        request.user = user

        html = cotton_render_string(
            '<c-stripe.pricing-table table_id="prctbl_test123" '
            'publishable_key="pk_test_456" customer_session_client_secret="cuss_s_1" '
            'customer_email="explicit@example.com" />',
            context={"request": request},
        )

        assert 'customer-session-client-secret="cuss_s_1"' in html
        assert "customer-email" not in html

    def test_renders_completely_from_its_attributes_alone_for_an_anonymous_visitor(
        self, cotton_render_string, rf, django_assert_num_queries, db
    ):
        request = rf.get("/")
        request.user = AnonymousUser()

        with django_assert_num_queries(0):
            html = cotton_render_string(
                "<article><h2>Order summary</h2>"
                '<c-stripe.pricing-table table_id="prctbl_test123" '
                'publishable_key="pk_test_456" /></article>',
                context={"request": request},
            )

        assert "Order summary" in html
        assert "<stripe-pricing-table" in html
        assert 'pricing-table-id="prctbl_test123"' in html
        assert 'publishable-key="pk_test_456"' in html
        assert "customer-email" not in html


class TestAmount:
    def test_no_amount_renders_nothing(self, cotton_render):
        html = cotton_render("stripe.amount", amount=None)

        assert html.strip() == ""

    def test_renders_the_amount_it_was_given(self, cotton_render):
        html = cotton_render(
            "stripe.amount", amount=Money(minor_units=2000, currency="USD")
        )

        assert "20.00 USD" in html

    def test_a_currencyless_amount_renders_nothing_for_the_figure(self, cotton_render):
        html = cotton_render(
            "stripe.amount", amount=Money(minor_units=2000, currency="")
        )

        assert "2000" not in html
        assert "20.00" not in html


def current_subscription(**overrides):
    fields = {
        "status": "active",
        "name": "Premium monthly",
        "amount": Money(minor_units=2500, currency="USD"),
        "interval": "month",
        "interval_count": 1,
        "period_start": None,
        "period_end": None,
    }
    return CurrentSubscription(**{**fields, **overrides})


class TestSubscription:
    def test_renders_the_status_name_amount_and_frequency(self, cotton_render):
        html = cotton_render("stripe.subscription", subscription=current_subscription())

        assert "active" in html
        assert "Premium monthly" in html
        assert "25.00 USD" in html
        assert "every month" in html

    def test_renders_a_recorded_period(self, cotton_render):
        now = timezone.now()
        subscription = current_subscription(period_start=now, period_end=now)

        html = cotton_render("stripe.subscription", subscription=subscription)

        assert str(now.year) in html

    def test_an_unrecognised_status_renders_as_itself_with_no_special_variant(
        self, cotton_render
    ):
        html = cotton_render(
            "stripe.subscription", subscription=current_subscription(status="paused")
        )

        assert "paused" in html

    def test_an_unrecognised_interval_renders_as_itself(self, cotton_render):
        subscription = current_subscription(interval="fortnight")

        html = cotton_render("stripe.subscription", subscription=subscription)

        assert "fortnight_1" in html

    def test_a_price_with_no_fixed_amount_shows_no_figure(self, cotton_render):
        html = cotton_render(
            "stripe.subscription", subscription=current_subscription(amount=None)
        )

        assert "None" not in html
        assert "Premium monthly" in html


class TestPlansLink:
    def test_a_subscriber_is_offered_a_switch_through_the_plan_change_endpoint(
        self, cotton_render
    ):
        html = cotton_render(
            "stripe.plans-link",
            url="/account/billing/plans/",
            subscribed=True,
            switch_endpoint="/api/plan-switch/",
        )

        assert "<button" in html
        assert "data-mvp-payments-portal-link" in html
        assert 'data-endpoint="/api/plan-switch/"' in html
        assert re.search(r'data-csrf-token="[^"]+"', html)
        assert re.search(
            r'<p hidden role="alert" data-mvp-payments-portal-link-failure', html
        )
        assert re.search(
            r'<p hidden role="alert" data-mvp-payments-portal-link-stale[^>]*>\s*'
            r"This page is out of date\. Reload it and try again\.",
            html,
        )
        assert "/account/billing/plans/" not in html

    def test_a_subscriber_with_no_plan_change_endpoint_is_offered_nothing(
        self, cotton_render
    ):
        html = cotton_render(
            "stripe.plans-link", url="/account/billing/plans/", subscribed=True
        )

        assert html.strip() == ""

    def test_somebody_on_no_plan_is_offered_a_choice(self, cotton_render):
        html = cotton_render(
            "stripe.plans-link", url="/account/billing/plans/", subscribed=False
        )

        assert 'href="/account/billing/plans/"' in html
        assert "data-mvp-payments-portal-link" not in html

    def test_given_no_address_it_renders_nothing_at_all(self, cotton_render):
        html = cotton_render("stripe.plans-link", url=None)

        assert html.strip() == ""


class TestProviderReturn:
    """``<c-stripe.provider-return>`` — waiting on a payment to arrive."""

    def test_renders_nothing_without_a_state(self, cotton_render):
        assert cotton_render("stripe.provider-return", state=None).strip() == ""

    def test_while_polling_it_says_the_payment_is_being_confirmed(self, cotton_render):
        html = cotton_render(
            "stripe.provider-return",
            state={"attempt": 1, "poll_url": "/billing/?returned=2"},
        )

        assert 'role="alert"' in html
        assert "Confirming your payment" in html

    def test_out_of_polls_it_says_to_reload_later(self, cotton_render):
        html = cotton_render(
            "stripe.provider-return",
            state={"attempt": 5, "poll_url": None},
        )

        assert "Reload this page later." in html
        assert "Confirming your payment" not in html


class TestSignInNotice:
    def test_it_asks_for_a_sign_in_and_leads_to_the_given_address(self, cotton_render):
        html = cotton_render(
            "stripe.sign-in-notice", url="/accounts/login/?next=/account/billing/plans/"
        )

        assert 'href="/accounts/login/?next=/account/billing/plans/"' in html

    def test_given_no_address_it_renders_nothing_at_all(self, cotton_render):
        assert cotton_render("stripe.sign-in-notice", url=None).strip() == ""


class TestPortalLink:
    def test_given_an_endpoint_it_renders_a_control_carrying_it_and_a_csrf_token(
        self, cotton_render
    ):
        html = cotton_render(
            "stripe.portal-link", endpoint="/api/stripe/customer-portal/"
        )

        assert 'data-endpoint="/api/stripe/customer-portal/"' in html
        assert re.search(r'data-csrf-token="[^"]+"', html)
        assert "<button" in html
        assert re.search(r'aria-describedby="([\w-]+)"', html)
        note_id = re.search(r'aria-describedby="([\w-]+)"', html).group(1)
        assert f'id="{note_id}"' in html
        assert re.search(
            r'<p hidden role="alert" data-mvp-payments-portal-link-failure', html
        )
        assert re.search(
            r'<p hidden role="alert" data-mvp-payments-portal-link-stale', html
        )

    def test_given_no_endpoint_it_states_the_provider_manages_it_and_renders_no_control(
        self, cotton_render
    ):
        html = cotton_render("stripe.portal-link", endpoint=None)

        assert "<button" not in html
        assert "provider" in html.lower()
        assert "cannot be reached" in html.lower()


class TestNoSubscription:
    def test_renders_one_line_given_nothing(self, cotton_render):
        html = cotton_render("stripe.no-subscription")

        assert "You don't have an active subscription." in html


class TestPlansUnavailable:
    def test_renders_its_sentence_given_nothing(self, cotton_render):
        html = cotton_render("stripe.plans-unavailable")

        assert "mvp-list-empty" in html


class TestStandalone:
    def test_amount_renders_inside_an_unrelated_template(self, cotton_render_string):
        html = cotton_render_string(
            '<article><h2>Order summary</h2><c-stripe.amount :amount="amount" /></article>',
            context={"amount": Money(minor_units=2000, currency="USD")},
        )

        assert "Order summary" in html
        assert "20.00 USD" in html

    def test_subscription_renders_inside_an_unrelated_template(
        self, cotton_render_string
    ):
        subscription = current_subscription()

        html = cotton_render_string(
            "<aside><h3>Dashboard widget</h3>"
            '<c-stripe.subscription :subscription="subscription" /></aside>',
            context={"subscription": subscription},
        )

        assert "Dashboard widget" in html
        assert "active" in html

    def test_portal_link_renders_inside_an_unrelated_template(
        self, cotton_render_string
    ):
        html = cotton_render_string(
            '<nav><span>Account</span><c-stripe.portal-link :endpoint="endpoint" /></nav>',
            context={"endpoint": "/api/stripe/customer-portal/"},
        )

        assert "Account" in html
        assert 'data-endpoint="/api/stripe/customer-portal/"' in html
        assert re.search(r'data-csrf-token="[^"]+"', html)

    def test_no_subscription_renders_inside_an_unrelated_template(
        self, cotton_render_string
    ):
        html = cotton_render_string(
            "<main><h1>Welcome</h1><c-stripe.no-subscription /></main>"
        )

        assert "Welcome" in html
        assert "You don't have an active subscription." in html
