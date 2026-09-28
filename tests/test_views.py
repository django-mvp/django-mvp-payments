"""Rendering a contributed page inside the Account Center layout."""

import re

import pytest
from django.conf import settings
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.factories import (
    FeatureFactory,
    PriceFactory,
    ProductFeatureFactory,
    StripeUserFactory,
    SubscriptionFactory,
    SubscriptionItemFactory,
    UserFactory,
)
from tests.markup import account_center_cards_region, account_navigation_regions
from tests.probes import run_probe

_AMOUNT_PATTERN = re.compile(r"\d[\d,]*\.\d{2,3} [A-Z]{3}")

_ACCOUNT_CENTER_WITH_ANOTHER_CARD_PROBE = """
import json

import django

django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)
User.objects.create_user(username="person", password="password")
client = Client()
client.login(username="person", password="password")
response = client.get("/account/")

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
}))
"""

_TEMPLATE_OVERRIDE_PROBE = """
import json

import django

django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import reverse

from tests.factories import (
    PriceFactory,
    StripeUserFactory,
    SubscriptionFactory,
    SubscriptionItemFactory,
)

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)

user = User.objects.create_user(username="person", password="password")
stripe_user = StripeUserFactory(user=user)
subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
price = PriceFactory(product__name="Premium", price=2000, currency="USD", freq="month_1")
SubscriptionItemFactory(subscription=subscription, price=price)

client = Client()
client.login(username="person", password="password")
response = client.get(reverse("payments:drf-stripe-subscription"))

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
}))
"""

_COMPONENT_TEMPLATE_OVERRIDE_PROBE = """
import json

import django

django.setup()

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.template import Context, Template
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext, setup_test_environment
from django_cotton.compiler_regex import CottonCompiler

setup_test_environment()

compiler = CottonCompiler()
request = RequestFactory().get("/")
request.user = AnonymousUser()

compiled = compiler.process(
    '<c-drf-stripe.pricing-table table_id="prctbl_test123" '
    'publishable_key="pk_test_456" />'
)
template = Template(compiled)
context = Context({"request": request})
context.request = request

with CaptureQueriesContext(connection) as captured:
    html = template.render(context)

print(json.dumps({"html": html, "query_count": len(captured)}))
"""

_PLANS_PAGE_TEMPLATE_OVERRIDE_PROBE = """
import json

import django

django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, override_settings
from django.test.utils import setup_test_environment
from django.urls import reverse

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)

User.objects.create_user(username="person", password="password")
client = Client()
client.login(username="person", password="password")

with override_settings(
    MVP_PAYMENTS={
        "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_test123",
        "DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_456",
    }
):
    response = client.get(reverse("payments:drf-stripe-plans"))

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
}))
"""


class TestPaymentPage:
    @pytest.mark.parametrize("page", drf_stripe.pages, ids=lambda page: page.slug)
    def test_signed_in_person_sees_the_page_inside_the_account_center(
        self, logged_in_client, page
    ):
        response = logged_in_client.get(reverse(drf_stripe.view_name(page)))
        content = response.content.decode()

        assert response.status_code == 200
        assert re.search(rf"<h1[^>]*>\s*{page.label}\s*</h1>", content)
        assert 'aria-label="Account navigation"' in content

    def test_anonymous_visitor_is_sent_to_the_sign_in_page(self, client, db):
        response = client.get(reverse("payments:drf-stripe-subscription"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))


def _content_region(content: str) -> str:
    """The page's content, with the Account Center's navigation cut out.

    "Plans" is also the navigation's label for this page, and django-mvp draws that
    navigation twice (``tests.markup``). Cutting both copies out narrows an assertion
    about the page's own content to markup nothing else could have produced.
    """
    for region in account_navigation_regions(content):
        content = content.replace(region, "")
    return content


@pytest.mark.django_db
class TestPlansPage:
    def test_context_and_content_carry_both_settings_values(self, logged_in_client):
        with override_settings(
            MVP_PAYMENTS={
                "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_test123",
                "DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_456",
            }
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-plans"))

        assert response.status_code == 200
        assert response.context["pricing_table_id"] == "prctbl_test123"
        assert response.context["publishable_key"] == "pk_test_456"

        content = _content_region(response.content.decode())
        assert "<stripe-pricing-table" in content
        assert 'pricing-table-id="prctbl_test123"' in content
        assert 'publishable-key="pk_test_456"' in content

    def test_the_element_carries_the_signed_in_persons_own_address(
        self, logged_in_client, user
    ):
        user.email = "person@example.com"
        user.save()

        with override_settings(
            MVP_PAYMENTS={
                "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_test123",
                "DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_456",
            }
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-plans"))

        content = _content_region(response.content.decode())
        assert 'customer-email="person@example.com"' in content

    def test_a_subscriber_is_sent_to_their_subscription_instead_of_the_table(
        self, subscriber_client
    ):
        with override_settings(
            MVP_PAYMENTS={
                "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_test123",
                "DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_456",
            }
        ):
            response = subscriber_client.get(reverse("payments:drf-stripe-plans"))

        content = _content_region(response.content.decode())
        assert response.status_code == 200
        assert "stripe-pricing-table" not in content
        assert f'href="{reverse("payments:drf-stripe-subscription")}"' in content

    def test_an_anonymous_visitor_is_sent_to_the_sign_in_page(self, client, db):
        response = client.get(reverse("payments:drf-stripe-plans"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))

    def test_renders_with_mvp_payments_absent_from_settings_entirely(
        self, logged_in_client, settings
    ):
        del settings.MVP_PAYMENTS

        response = logged_in_client.get(reverse("payments:drf-stripe-plans"))

        assert response.status_code == 200
        assert response.context["pricing_table_id"] is None
        assert response.context["publishable_key"] is None

    def test_importing_the_views_module_with_settings_unconfigured_raises_nothing(self):
        import importlib

        import mvp_payments.views as views_module

        importlib.reload(views_module)

    def test_states_plans_unavailable_and_emits_no_provider_element_without_a_table_id(
        self, logged_in_client
    ):
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_PUBLISHABLE_KEY": "pk_test_456"}
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-plans"))

        content = _content_region(response.content.decode())
        assert response.status_code == 200
        assert "stripe-pricing-table" not in content
        assert "Plans not available" in content

    def test_states_plans_unavailable_and_emits_no_provider_element_without_a_publishable_key(
        self, logged_in_client
    ):
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_PRICING_TABLE_ID": "prctbl_test123"}
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-plans"))

        content = _content_region(response.content.decode())
        assert response.status_code == 200
        assert "stripe-pricing-table" not in content
        assert "Plans not available" in content

    def test_with_mvp_payments_absent_the_heading_and_navigation_render_unchanged(
        self, logged_in_client, settings
    ):
        del settings.MVP_PAYMENTS

        response = logged_in_client.get(reverse("payments:drf-stripe-plans"))
        content = response.content.decode()

        assert response.status_code == 200
        plans_label = drf_stripe.pages[1].label
        assert re.search(rf"<h1[^>]*>\s*{plans_label}\s*</h1>", content)
        assert 'aria-label="Account navigation"' in content
        assert "stripe-pricing-table" not in content
        assert "Plans not available" in _content_region(content)


class TestPageViewConfiguration:
    def test_a_view_with_no_contribution_says_what_is_missing(self):
        from django.core.exceptions import ImproperlyConfigured

        from mvp_payments.views import SubscriptionPageView

        with pytest.raises(ImproperlyConfigured, match="requires `contribution`"):
            SubscriptionPageView().get_contribution()


class TestAccountCenterOverview:
    def _open_the_account_center_with_another_card(self) -> dict:
        # sys.executable and a module-level string constant, no untrusted input.
        return run_probe(
            _ACCOUNT_CENTER_WITH_ANOTHER_CARD_PROBE,
            "tests.settings_with_another_card",
        )

    def test_shows_the_installed_backends_card_and_keeps_other_apps_cards(self):
        result = self._open_the_account_center_with_another_card()

        assert result["status_code"] == 200
        cards = account_center_cards_region(result["content"])

        expected_url = reverse("payments:drf-stripe-subscription")
        assert cards.count(f'href="{expected_url}"') == 1
        assert cards.count('data-testid="other-app-card"') == 1


class TestURLsNotMounted:
    def test_account_center_renders_with_nothing_from_the_unmounted_backend(
        self, logged_in_client
    ):
        with override_settings(ROOT_URLCONF="tests.urls_without_payments"):
            response = logged_in_client.get(reverse("account-center"))

        assert response.status_code == 200
        content = response.content.decode()

        # The page itself still renders, with its own navigation intact — an
        # unmounted backend is not a broken page.
        assert 'aria-label="Account navigation"' in content

        # No navigation entry: covers every one of the backend's pages.
        for page in drf_stripe.pages:
            assert f"<span>{page.label}</span>" not in content

        # The group goes with its pages. django-flex-menus hides a container
        # left with no visible children, so the label cannot outlive the
        # entries it was heading.
        for region in account_navigation_regions(content):
            assert f">{drf_stripe.group_label}<" not in region

        # No card: its link would need a URL name that cannot reverse here.
        cards = account_center_cards_region(content)
        assert "<a href" not in cards
        for page in drf_stripe.pages:
            assert f">{page.label}<" not in cards


@pytest.mark.django_db
class TestSubscriptionPage:
    def test_renders_the_plan_name_amount_frequency_and_status(
        self, subscriber_client, user
    ):
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "active" in content
        assert "20.00" in content or "10.00" in content  # sanity: some amount renders
        assert _AMOUNT_PATTERN.search(content)

    def test_a_recorded_period_appears(self, subscriber_client, current_subscription):
        current_subscription.period_start = timezone.now()
        current_subscription.period_end = timezone.now()
        current_subscription.save()

        content = subscriber_client.get(
            reverse("payments:drf-stripe-subscription")
        ).content.decode()

        assert str(current_subscription.period_start.year) in content

    def test_a_subscription_with_no_period_recorded_still_renders_the_rest(
        self, subscriber_client, current_subscription
    ):
        current_subscription.period_start = None
        current_subscription.period_end = None
        current_subscription.save()

        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))

        assert response.status_code == 200
        assert "active" in response.content.decode()

    def test_two_priced_items_show_both_amounts_and_no_third_figure(
        self, user, client_for
    ):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
        first_price = PriceFactory(price=2000, currency="USD", freq="month_1")
        second_price = PriceFactory(price=3000, currency="EUR", freq="month_1")
        SubscriptionItemFactory(subscription=subscription, price=first_price)
        SubscriptionItemFactory(subscription=subscription, price=second_price)

        client = client_for(user)
        content = client.get(
            reverse("payments:drf-stripe-subscription")
        ).content.decode()

        assert set(_AMOUNT_PATTERN.findall(content)) == {"20.00 USD", "30.00 EUR"}

    def test_an_unrecognised_status_renders_as_itself(self, user, client_for):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="past_due")
        SubscriptionItemFactory(subscription=subscription)

        client = client_for(user)
        content = client.get(
            reverse("payments:drf-stripe-subscription")
        ).content.decode()

        assert "past_due" in content

    def test_another_persons_subscription_never_appears(self, subscriber_client):
        other_stripe_user = StripeUserFactory()
        other_subscription = SubscriptionFactory(
            stripe_user=other_stripe_user, status="active"
        )
        other_price = PriceFactory(
            price=999999, currency="GBP", product__name="Nobody Else's Plan"
        )
        SubscriptionItemFactory(subscription=other_subscription, price=other_price)

        content = subscriber_client.get(
            reverse("payments:drf-stripe-subscription")
        ).content.decode()

        assert "Nobody Else's Plan" not in content
        assert "9,999.99 GBP" not in content

    def test_a_fixed_number_of_queries_whatever_the_number_of_items(
        self, user, client_for
    ):
        one_item_user = user
        stripe_user_one = StripeUserFactory(user=one_item_user)
        subscription_one = SubscriptionFactory(
            stripe_user=stripe_user_one, status="active"
        )
        SubscriptionItemFactory(subscription=subscription_one)

        many_items_user = UserFactory()
        stripe_user_many = StripeUserFactory(user=many_items_user)
        subscription_many = SubscriptionFactory(
            stripe_user=stripe_user_many, status="active"
        )
        for _ in range(4):
            SubscriptionItemFactory(subscription=subscription_many)

        client_one = client_for(one_item_user)
        client_many = client_for(many_items_user)
        page_url = reverse("payments:drf-stripe-subscription")

        # A first request warms process-wide caches (the site, content types), so both
        # clients are primed to keep the comparison about the page's own queries.
        client_one.get(page_url)
        client_many.get(page_url)

        with CaptureQueriesContext(connection) as captured_one:
            client_one.get(page_url)
        with CaptureQueriesContext(connection) as captured_many:
            client_many.get(page_url)

        assert len(captured_one) == len(captured_many)

    def test_the_page_loads_the_portal_script(self, subscriber_client):
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "data-mvp-payments-portal-link" in content
        assert 'src="/static/mvp_payments/drf_stripe/billing_portal.js"' in content

    def test_a_subscriber_switches_through_the_plan_change_endpoint(
        self, subscriber_client
    ):
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_PLAN_SWITCH": "/api/plan-switch/"}
        ):
            response = subscriber_client.get(
                reverse("payments:drf-stripe-subscription")
            )
        content = _content_region(response.content.decode())

        assert response.context["plan_switch_endpoint"] == "/api/plan-switch/"
        assert 'data-endpoint="/api/plan-switch/"' in content
        assert f'href="{reverse("payments:drf-stripe-plans")}"' not in content

    def test_without_a_plan_change_endpoint_a_subscriber_is_offered_no_switch(
        self, subscriber_client
    ):
        with override_settings(MVP_PAYMENTS={}):
            response = subscriber_client.get(
                reverse("payments:drf-stripe-subscription")
            )
        content = _content_region(response.content.decode())

        assert response.context["plan_switch_endpoint"] is None
        assert "data-mvp-payments-portal-link" not in content

    def test_the_plan_change_endpoint_is_withheld_from_somebody_with_no_subscription(
        self, user, client_for
    ):
        client = client_for(user)
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_PLAN_SWITCH": "/api/plan-switch/"}
        ):
            response = client.get(reverse("payments:drf-stripe-subscription"))

        assert response.context["plan_switch_endpoint"] is None
        assert "/api/plan-switch/" not in response.content.decode()

    def test_someone_with_no_subscription_is_invited_to_choose_one(
        self, user, client_for
    ):
        client = client_for(user)

        response = client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert f'href="{reverse("payments:drf-stripe-plans")}"' in content
        assert "data-mvp-payments-portal-link" not in content

    def test_the_portal_control_carries_a_usable_csrf_token(self, subscriber_client):
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        token = re.search(r'data-csrf-token="([^"]*)"', content)
        assert token is not None
        assert len(token.group(1)) > 20


@pytest.mark.django_db
class TestBillingPortalEndpoint:
    def test_carries_the_endpoint_from_settings_for_a_current_subscriber(
        self, subscriber_client
    ):
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_BILLING_PORTAL": "/api/stripe/customer-portal/"}
        ):
            response = subscriber_client.get(
                reverse("payments:drf-stripe-subscription")
            )

        assert (
            response.context["billing_portal_endpoint"]
            == "/api/stripe/customer-portal/"
        )

    def test_is_none_when_the_setting_is_absent(self, subscriber_client):
        with override_settings(MVP_PAYMENTS={}):
            response = subscriber_client.get(
                reverse("payments:drf-stripe-subscription")
            )

        assert response.context["billing_portal_endpoint"] is None

    def test_is_none_for_a_person_with_no_current_subscription_even_when_set(
        self, logged_in_client
    ):
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_BILLING_PORTAL": "/api/stripe/customer-portal/"}
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-subscription"))

        assert response.context["billing_portal_endpoint"] is None

    def test_says_nothing_about_a_subscription_to_someone_who_has_none(
        self, logged_in_client
    ):
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_BILLING_PORTAL": "/api/stripe/customer-portal/"}
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-subscription"))

        content = response.content.decode()
        assert "data-mvp-payments-portal-link" not in content
        assert "managed by the provider" not in content
        assert "cannot be reached" not in content


@pytest.mark.django_db
class TestNoCurrentSubscription:
    def test_a_person_whose_subscription_has_ended_is_told_there_is_none(
        self, user, client_for
    ):
        stripe_user = StripeUserFactory(user=user)
        ended_subscription = SubscriptionFactory(
            stripe_user=stripe_user, status="canceled"
        )
        ended_subscription.period_start = timezone.now()
        ended_subscription.period_end = timezone.now()
        ended_subscription.save()
        feature = FeatureFactory(description="Priority support")
        price = PriceFactory(
            product__name="Nobody's Plan Anymore",
            price=999999,
            currency="GBP",
            freq="year_1",
        )
        ProductFeatureFactory(product=price.product, feature=feature)
        SubscriptionItemFactory(subscription=ended_subscription, price=price)

        client = client_for(user)
        response = client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "You don't have an active subscription." in content
        assert "Nobody's Plan Anymore" not in content
        assert "9,999.99 GBP" not in content
        assert "every year" not in content
        assert "canceled" not in content
        assert str(ended_subscription.period_start.year) not in content
        assert "Priority support" not in content
        assert "data-mvp-payments-portal-link" not in content

    def test_a_person_with_no_customer_record_at_all_reaches_the_same_page(
        self, logged_in_client
    ):
        response = logged_in_client.get(reverse("payments:drf-stripe-subscription"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "You don't have an active subscription." in content
        assert "data-mvp-payments-portal-link" not in content


class TestTemplateOverride:
    def _open_the_overridden_page(self) -> dict:
        return run_probe(
            _TEMPLATE_OVERRIDE_PROBE, "tests.settings_with_project_template_override"
        )

    def test_every_documented_context_value_reaches_the_projects_own_template(self):
        result = self._open_the_overridden_page()

        assert result["status_code"] == 200
        content = result["content"]
        # The marker only the project's own template carries — proves this rendered
        # instead of the shipped page, not merely that the page rendered at all.
        assert 'data-testid="the-hosting-projects-own-subscription-page"' in content
        assert "active" in content
        assert "Premium" in content
        assert "20.00 USD" in content
        assert "every month" in content
        # Read from the configuration rather than written out here: which endpoint a
        # project hands a reader to is the project's to choose, and what this proves is
        # that the value reaches the project's own template, not what the value is.
        assert settings.MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"] in content


class TestPlansPageOverride:
    def test_a_projects_own_component_renders_with_no_view_and_no_query(self):
        result = run_probe(
            _COMPONENT_TEMPLATE_OVERRIDE_PROBE,
            "tests.settings_with_project_template_override",
        )

        assert result["query_count"] == 0
        html = result["html"]
        assert 'data-testid="the-hosting-projects-own-pricing-table"' in html
        assert 'data-table-id="prctbl_test123"' in html
        assert 'data-publishable-key="pk_test_456"' in html

    def test_a_projects_own_page_template_receives_every_documented_context_name(self):
        result = run_probe(
            _PLANS_PAGE_TEMPLATE_OVERRIDE_PROBE,
            "tests.settings_with_project_template_override",
        )

        assert result["status_code"] == 200
        content = result["content"]
        assert 'data-testid="the-hosting-projects-own-plans-page"' in content
        assert '<p data-testid="pricing-table-id">prctbl_test123</p>' in content
        assert '<p data-testid="publishable-key">pk_test_456</p>' in content
        assert 'data-testid="the-hosting-projects-own-pricing-table"' in content
