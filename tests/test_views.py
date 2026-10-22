"""Rendering a contributed page inside the Account Center layout."""

import html
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from mvp_payments.namespaces.stripe import stripe_contribution
from mvp_payments.views import SubscriptionPageView
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
    UserFactory,
)
from tests.markup import account_center_cards_region, account_navigation_regions
from tests.probes import run_probe
from tests.stripe_fake import price_payload, product_payload

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

from tests.factories import StripeSubscriptionFactory

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)

user = User.objects.create_user(username="person", password="password")
StripeSubscriptionFactory(
    customer__user=user,
    status="active",
    product_name="Premium",
    amount=2000,
    currency="usd",
    interval="month",
    interval_count=1,
)

client = Client()
client.login(username="person", password="password")
response = client.get(reverse("payments:stripe-subscription"))

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
}))
"""

_PLANS_PAGE_TEMPLATE_OVERRIDE_PROBE = """
import json

import django

django.setup()

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import reverse

from mvp_payments.stripe.catalogue import Catalogue

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)

# The catalogue is cached, so the probe never asks Stripe.
cache.set(
    Catalogue.KEY,
    [
        {
            "id": "price_probe",
            "unit_amount": 2000,
            "currency": "usd",
            "recurring": {"interval": "month", "interval_count": 1},
            "product": {"id": "prod_probe", "name": "Probe", "marketing_features": []},
        }
    ],
    3600,
)
response = Client().get(reverse("payments_plans:stripe-plans"))

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
}))
"""


class TestPaymentPage:
    @pytest.mark.parametrize(
        "page", stripe_contribution.pages, ids=lambda page: page.slug
    )
    def test_signed_in_person_sees_the_page_inside_the_account_center(
        self, logged_in_client, page
    ):
        response = logged_in_client.get(reverse(stripe_contribution.view_name(page)))
        content = response.content.decode()

        assert response.status_code == 200
        assert re.search(rf"<h1[^>]*>\s*{page.label}\s*</h1>", content)
        # django-mvp swaps the sidebar to the Account Center's navigation on a page
        # that navigation has an entry for, and on no other.
        assert ('aria-label="Account navigation"' in content) == page.in_navigation

    def test_anonymous_visitor_is_sent_to_the_sign_in_page(self, client, db):
        response = client.get(reverse("payments:stripe-subscription"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("account_login"))


def _content_region(content: str) -> str:
    """The page's content, with the Account Center's navigation cut out.

    A page's label can also be a navigation entry's (``tests.markup``). Cutting the
    navigation out narrows an assertion about the page's own content to markup nothing
    else could have produced.
    """
    for region in account_navigation_regions(content):
        content = content.replace(region, "")
    return content


def _card(content: str, price_id: str) -> str:
    """The markup of the plan card for one price, up to the next card or the page's note."""
    start = content.index(f'id="{price_id}"')
    ends = [
        content.find(marker, start + 1)
        for marker in (' id="price_', 'id="mvp-payments-checkout-note"')
    ]
    return content[start : min(end for end in ends if end != -1)]


@pytest.fixture
def plans_on_offer(stripe_fake):
    basic = {
        **product_payload("prod_basic", "Basic"),
        "active": True,
        "description": "For one person getting started.",
        "marketing_features": [{"name": "One project"}, {"name": "Email support"}],
    }
    bare = {**product_payload("prod_bare", "Bare"), "active": True}
    stripe_fake.respond_with_list(
        "/v1/prices",
        [
            price_payload("price_basic_month", basic, unit_amount=2000),
            price_payload(
                "price_basic_year", basic, unit_amount=20000, interval="year"
            ),
            price_payload("price_bare_yen", bare, unit_amount=500000, currency="jpy"),
            price_payload(
                "price_bare_dinar",
                bare,
                unit_amount=12500,
                currency="kwd",
                interval_count=3,
            ),
        ],
    )
    return stripe_fake


@pytest.mark.django_db
class TestPlansPage:
    def test_an_anonymous_visitor_opens_it_at_the_address_the_project_mounted_it(
        self, client, plans_on_offer
    ):
        response = client.get(reverse("payments_plans:stripe-plans"))

        assert reverse("payments_plans:stripe-plans") == "/plans/"
        assert response.status_code == 200

    def test_every_price_on_offer_has_a_card(self, client, plans_on_offer):
        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        for price_id in (
            "price_basic_month",
            "price_basic_year",
            "price_bare_yen",
            "price_bare_dinar",
        ):
            assert f'id="{price_id}"' in content

    def test_a_card_shows_the_name_amount_frequency_description_and_features(
        self, client, plans_on_offer
    ):
        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        card = _card(content, "price_basic_month")
        assert "Basic" in card
        assert "20.00 USD" in card
        assert "every month" in card
        assert "For one person getting started." in card
        assert "One project" in card
        assert "Email support" in card

    def test_each_price_of_one_product_shows_its_own_amount_and_frequency(
        self, client, plans_on_offer
    ):
        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        card = _card(content, "price_basic_year")
        assert "200.00 USD" in card
        assert "every year" in card

    @pytest.mark.parametrize(
        ("price_id", "amount", "frequency"),
        [
            ("price_bare_yen", "500,000 JPY", "every month"),
            ("price_bare_dinar", "12.500 KWD", "every 3 months"),
        ],
    )
    def test_an_amount_is_shown_in_its_own_currency_with_its_own_places(
        self, client, plans_on_offer, price_id, amount, frequency
    ):
        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        card = _card(content, price_id)
        assert amount in card
        assert frequency in card

    def test_a_product_with_no_description_or_features_shows_neither(
        self, client, plans_on_offer
    ):
        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        card = _card(content, "price_bare_yen")
        assert "None" not in card
        assert "<ul" not in card

    def test_text_from_stripe_is_escaped(self, client, stripe_fake):
        hostile = {
            **product_payload("prod_x", "<script>alert(1)</script>"),
            "active": True,
            "description": "<b>bold</b>",
            "marketing_features": [{"name": "<img src=x onerror=alert(2)>"}],
        }
        stripe_fake.respond_with_list("/v1/prices", [price_payload("price_x", hostile)])

        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content
        assert "<b>bold</b>" not in content
        assert "<img src=x" not in content

    def test_the_page_carries_no_pricing_table_and_no_provider_script(
        self, client, plans_on_offer
    ):
        content = client.get(reverse("payments_plans:stripe-plans")).content.decode()

        assert "stripe-pricing-table" not in content
        assert "js.stripe.com" not in content

    def test_a_catalogue_that_cannot_be_read_is_stated_and_offers_no_plan(
        self, client, stripe_fake
    ):
        stripe_fake.become_unreachable("GET", "/v1/prices")

        response = client.get(reverse("payments_plans:stripe-plans"))

        assert response.status_code == 200
        assert response.context["plans"]["prices"] is None
        content = response.content.decode()
        assert "mvp-list-empty" in content
        assert 'id="price_' not in content

    def test_a_missing_secret_key_is_stated_without_asking_stripe(
        self, client, stripe_fake, settings
    ):
        settings.MVP_PAYMENTS = {}

        response = client.get(reverse("payments_plans:stripe-plans"))

        assert response.status_code == 200
        assert response.context["plans"]["prices"] is None
        assert stripe_fake.requests == []

    def test_a_catalogue_with_nothing_on_offer_is_stated_and_offers_no_plan(
        self, client, stripe_fake
    ):
        stripe_fake.respond_with_list("/v1/prices", [])

        response = client.get(reverse("payments_plans:stripe-plans"))

        assert response.status_code == 200
        assert response.context["plans"]["prices"] == []
        content = response.content.decode()
        assert "mvp-list-empty" in content
        assert 'id="price_' not in content

    def test_a_plan_the_person_holds_is_marked_as_theirs(
        self, logged_in_client, user, plans_on_offer
    ):
        StripeSubscriptionFactory(
            customer__user=user, price_id="price_basic_month", status="active"
        )

        response = logged_in_client.get(reverse("payments_plans:stripe-plans"))

        assert response.context["plans"]["held"] == ["price_basic_month"]

    def test_a_second_visit_reads_the_catalogue_from_the_cache(
        self, client, plans_on_offer
    ):
        client.get(reverse("payments_plans:stripe-plans"))
        asked = len(plans_on_offer.requests)

        client.get(reverse("payments_plans:stripe-plans"))

        assert len(plans_on_offer.requests) == asked


@pytest.mark.django_db
class TestPlansWayToBuy:
    url = "/plans/"

    def page(self, client, **query):
        return client.get(self.url, query).content.decode()

    def test_a_visitor_who_is_not_signed_in_is_sent_to_sign_in_and_back_to_the_plan(
        self, client, plans_on_offer
    ):
        card = _card(self.page(client), "price_basic_year")

        (href,) = re.findall(r'href="([^"]*\?next=[^"]*)"', card)
        query = parse_qs(urlsplit(html.unescape(href)).query)
        assert query["next"] == ["/plans/?plan=price_basic_year#price_basic_year"]
        assert "<form" not in card

    def test_a_signed_in_person_gets_a_form_posting_the_price_to_the_checkout(
        self, logged_in_client, plans_on_offer
    ):
        card = _card(self.page(logged_in_client), "price_basic_year")

        assert 'method="post"' in card
        assert f'action="{reverse("payments:stripe-checkout")}"' in card
        assert 'name="price" value="price_basic_year"' in card
        assert 'name="return_to" value="/plans/"' in card
        assert "csrfmiddlewaretoken" in card

    def test_a_plan_the_person_holds_leads_to_their_subscriptions_not_the_checkout(
        self, logged_in_client, user, plans_on_offer
    ):
        StripeSubscriptionFactory(
            customer__user=user, price_id="price_basic_month", status="active"
        )
        content = self.page(logged_in_client)

        held = _card(content, "price_basic_month")
        other = _card(content, "price_basic_year")
        assert f'href="{reverse("payments:stripe-subscription")}"' in held
        assert "<form" not in held
        assert "<form" in other

    def test_a_plan_whose_subscription_ended_is_offered_again(
        self, logged_in_client, user, plans_on_offer
    ):
        StripeSubscriptionFactory(
            customer__user=user, price_id="price_basic_month", status="canceled"
        )

        card = _card(self.page(logged_in_client), "price_basic_month")

        assert "<form" in card
        assert reverse("payments:stripe-subscription") not in card

    def test_the_plan_picked_before_signing_in_has_its_frequency_selected(
        self, client, plans_on_offer
    ):
        content = self.page(client, plan="price_basic_year")

        assert "interval: 'year_1'" in content
        year = re.search(r"<input[^>]*value=\"year_1\"[^>]*>", content).group()
        month = re.search(r"<input[^>]*value=\"month_1\"[^>]*>", content).group()
        assert "checked" in year
        assert "checked" not in month
        assert 'id="price_basic_year"' in content

    @pytest.mark.parametrize("signed_in", [False, True])
    def test_each_control_is_named_for_its_plan_and_described_by_the_off_site_note(
        self, client, logged_in_client, plans_on_offer, signed_in
    ):
        content = self.page(logged_in_client if signed_in else client)

        card = _card(content, "price_basic_month")
        control = re.search(
            r"<(?:button|a)[^>]*aria-describedby=[^>]*>.*?</(?:button|a)>", card, re.S
        ).group()
        assert "Basic, every month" in control
        assert 'aria-describedby="mvp-payments-checkout-note"' in control
        note = content[content.index('id="mvp-payments-checkout-note"') :]
        assert "Stripe" in note.split("</p>")[0]

    def test_the_control_for_a_held_plan_is_named_for_the_subscription(
        self, logged_in_client, user, plans_on_offer
    ):
        StripeSubscriptionFactory(
            customer__user=user, price_id="price_basic_month", status="active"
        )

        card = _card(self.page(logged_in_client), "price_basic_month")

        assert "your Basic subscription" in card


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

        expected_url = reverse("payments:stripe-subscription")
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
        for page in stripe_contribution.pages:
            assert f"<span>{page.label}</span>" not in content

        # The group goes with its pages. django-flex-menus hides a container
        # left with no visible children, so the label cannot outlive the
        # entries it was heading.
        for region in account_navigation_regions(content):
            assert f">{stripe_contribution.group_label}<" not in region

        # No card: its link would need a URL name that cannot reverse here.
        cards = account_center_cards_region(content)
        assert "<a href" not in cards
        for page in stripe_contribution.pages:
            assert f">{page.label}<" not in cards


@pytest.mark.django_db
class TestSubscriptionPage:
    def test_renders_the_plan_name_amount_frequency_and_status(
        self, subscribed_client, stripe_subscription
    ):
        stripe_subscription.product_name = "Premium monthly"
        stripe_subscription.save()

        response = subscribed_client.get(reverse("payments:stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "active" in content
        assert "Premium monthly" in content
        assert "20.00 USD" in content
        assert "every month" in content

    def test_a_recorded_period_appears(self, subscribed_client, stripe_subscription):
        stripe_subscription.current_period_start = timezone.now()
        stripe_subscription.current_period_end = timezone.now()
        stripe_subscription.save()

        content = subscribed_client.get(
            reverse("payments:stripe-subscription")
        ).content.decode()

        assert str(stripe_subscription.current_period_start.year) in content

    def test_a_subscription_with_no_period_recorded_still_renders_the_rest(
        self, subscribed_client, stripe_subscription
    ):
        stripe_subscription.current_period_start = None
        stripe_subscription.current_period_end = None
        stripe_subscription.save()

        response = subscribed_client.get(reverse("payments:stripe-subscription"))

        assert response.status_code == 200
        assert "active" in response.content.decode()

    def test_every_subscription_the_person_holds_is_listed(self, user, client_for):
        customer = StripeCustomerFactory(user=user)
        StripeSubscriptionFactory(
            customer=customer, product_name="Basic", amount=2000, currency="usd"
        )
        StripeSubscriptionFactory(
            customer=customer,
            product_name="Extras",
            amount=3000,
            currency="eur",
            status="trialing",
        )

        content = (
            client_for(user)
            .get(reverse("payments:stripe-subscription"))
            .content.decode()
        )

        assert "Basic" in content
        assert "Extras" in content
        assert set(_AMOUNT_PATTERN.findall(content)) == {"20.00 USD", "30.00 EUR"}
        assert "trialing" in content

    def test_another_persons_subscription_never_appears(self, subscribed_client):
        StripeSubscriptionFactory(
            status="active",
            product_name="Nobody Else's Plan",
            amount=999999,
            currency="gbp",
        )

        content = subscribed_client.get(
            reverse("payments:stripe-subscription")
        ).content.decode()

        assert "Nobody Else's Plan" not in content
        assert "9,999.99 GBP" not in content

    def test_a_fixed_number_of_queries_whatever_the_number_of_subscriptions(
        self, user, client_for
    ):
        one_subscription_user = user
        StripeSubscriptionFactory(customer__user=one_subscription_user)

        many_subscriptions_user = UserFactory()
        customer = StripeCustomerFactory(user=many_subscriptions_user)
        for _ in range(4):
            StripeSubscriptionFactory(customer=customer)

        client_one = client_for(one_subscription_user)
        client_many = client_for(many_subscriptions_user)
        page_url = reverse("payments:stripe-subscription")

        # A first request warms process-wide caches (the site, content types), so both
        # clients are primed to keep the comparison about the page's own queries.
        client_one.get(page_url)
        client_many.get(page_url)

        with CaptureQueriesContext(connection) as captured_one:
            client_one.get(page_url)
        with CaptureQueriesContext(connection) as captured_many:
            client_many.get(page_url)

        assert len(captured_one) == len(captured_many)

    def test_the_page_loads_the_portal_script(self, subscribed_client):
        response = subscribed_client.get(reverse("payments:stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "data-mvp-payments-portal-link" in content
        assert 'src="/static/mvp_payments/stripe/billing_portal.js"' in content

    def test_a_subscriber_switches_through_the_apps_plan_switch_view(
        self, subscribed_client
    ):
        response = subscribed_client.get(reverse("payments:stripe-subscription"))
        content = _content_region(response.content.decode())
        endpoint = reverse("payments:stripe-plan-switch")

        assert response.context["plan_switch_endpoint"] == endpoint
        assert f'data-endpoint="{endpoint}"' in content
        assert f'href="{reverse("payments_plans:stripe-plans")}"' not in content

    def test_the_plan_switch_view_is_withheld_from_somebody_with_no_subscription(
        self, logged_in_client
    ):
        response = logged_in_client.get(reverse("payments:stripe-subscription"))

        assert response.context["plan_switch_endpoint"] is None
        assert reverse("payments:stripe-plan-switch") not in response.content.decode()

    def test_someone_with_no_subscription_is_invited_to_choose_one(
        self, user, client_for
    ):
        client = client_for(user)

        response = client.get(reverse("payments:stripe-subscription"))
        content = response.content.decode()

        assert f'href="{reverse("payments_plans:stripe-plans")}"' in content
        assert "data-mvp-payments-portal-link" not in content

    def test_the_plans_address_is_the_one_the_project_mounted(self, logged_in_client):
        response = logged_in_client.get(reverse("payments:stripe-subscription"))

        assert response.context["plans_url"] == reverse("payments_plans:stripe-plans")

    def test_nothing_leads_to_the_plans_when_the_project_has_not_mounted_them(
        self, logged_in_client
    ):
        with override_settings(ROOT_URLCONF="tests.urls_without_plans"):
            response = logged_in_client.get(reverse("payments:stripe-subscription"))

        assert response.status_code == 200
        assert response.context["plans_url"] is None
        assert "/plans/" not in response.content.decode()

    def test_the_portal_control_carries_a_usable_csrf_token(self, subscribed_client):
        response = subscribed_client.get(reverse("payments:stripe-subscription"))
        content = response.content.decode()

        token = re.search(r'data-csrf-token="([^"]*)"', content)
        assert token is not None
        assert len(token.group(1)) > 20


@pytest.mark.django_db
class TestComingBackFromTheProvider:
    """``?returned=N``: the reader has just come back from paying at the provider.

    The provider tells the backend about the payment separately from sending the reader back, so
    the page can be reached before the backend knows anything changed.
    """

    def _page(self, client, query=""):
        return client.get(reverse("payments:stripe-subscription") + query)

    def _region(self, response):
        """The subscription region's opening tag, where the polling is declared."""
        return re.search(
            r'<div id="mvp-payments-subscription"[^>]*>', response.content.decode()
        ).group(0)

    def test_an_ordinary_visit_carries_no_return_state(self, logged_in_client):
        response = self._page(logged_in_client)

        assert response.context["provider_return"] is None
        assert "hx-trigger" not in self._region(response)
        content = _content_region(response.content.decode())
        assert "You don't have an active subscription." in content

    def test_just_paid_with_nothing_showing_yet_is_told_it_is_being_confirmed(
        self, logged_in_client
    ):
        """Never "you don't have an active subscription" to somebody who has just paid."""
        response = self._page(logged_in_client, "?returned=1")

        content = _content_region(response.content.decode())
        assert "Confirming your payment with the provider." in content
        assert "You don't have an active subscription." not in content

    def test_while_waiting_the_region_polls_for_itself_and_counts_up(
        self, logged_in_client
    ):
        """Only the region is fetched and swapped, not the whole page reloaded."""
        region = self._region(self._page(logged_in_client, "?returned=1"))

        page = reverse("payments:stripe-subscription")
        assert f'hx-get="{page}?returned=2"' in region
        assert 'hx-trigger="every 3s"' in region
        assert 'hx-select="#mvp-payments-subscription"' in region
        assert 'hx-swap="outerHTML"' in region

    def test_the_polling_stops_once_the_limit_is_reached(self, logged_in_client):
        limit = SubscriptionPageView.RETURN_POLL_LIMIT

        response = self._page(logged_in_client, f"?returned={limit}")

        assert response.context["provider_return"]["poll_url"] is None
        assert "hx-trigger" not in self._region(response)
        content = _content_region(response.content.decode())
        assert "Your payment hasn't reached this site yet." in content
        assert "You don't have an active subscription." not in content

    def test_with_a_subscription_showing_there_is_nothing_to_wait_for(
        self, subscribed_client
    ):
        """The poll that finds the payment stops polling, and a reload says nothing more.

        This is also what somebody back from the portal sees: the page cannot tell whether a
        change made there has landed yet, so it shows the subscription as it stands.
        """
        response = self._page(subscribed_client, "?returned=3")

        assert response.context["provider_return"] is None
        assert "hx-trigger" not in self._region(response)
        content = _content_region(response.content.decode())
        assert "Confirming your payment" not in content
        assert "hasn't reached this site yet" not in content

    @pytest.mark.parametrize("value", ["", "abc", "0", "-4"])
    def test_a_malformed_count_is_read_as_the_first_return(
        self, logged_in_client, value
    ):
        response = self._page(logged_in_client, f"?returned={value}")

        assert response.context["provider_return"]["attempt"] == 1


@pytest.mark.django_db
class TestBillingPortalEndpoint:
    def test_is_the_apps_billing_portal_view_for_a_current_subscriber(
        self, subscribed_client
    ):
        response = subscribed_client.get(reverse("payments:stripe-subscription"))

        endpoint = reverse("payments:stripe-billing-portal")
        assert response.context["billing_portal_endpoint"] == endpoint
        assert f'data-endpoint="{endpoint}"' in response.content.decode()

    def test_is_none_for_a_person_with_no_current_subscription(self, logged_in_client):
        response = logged_in_client.get(reverse("payments:stripe-subscription"))

        assert response.context["billing_portal_endpoint"] is None

    def test_says_nothing_about_a_subscription_to_someone_who_has_none(
        self, logged_in_client
    ):
        response = logged_in_client.get(reverse("payments:stripe-subscription"))

        content = response.content.decode()
        assert "data-mvp-payments-portal-link" not in content
        assert "managed by the provider" not in content
        assert "cannot be reached" not in content


@pytest.mark.django_db
class TestNoCurrentSubscription:
    @pytest.mark.parametrize("status", ["canceled", "incomplete_expired"])
    def test_a_person_whose_subscription_has_finished_is_told_there_is_none(
        self, user, client_for, status
    ):
        ended_subscription = StripeSubscriptionFactory(
            customer__user=user,
            status=status,
            product_name="Nobody's Plan Anymore",
            amount=999999,
            currency="gbp",
            interval="year",
            current_period_start=timezone.now(),
            current_period_end=timezone.now(),
        )

        client = client_for(user)
        response = client.get(reverse("payments:stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "You don't have an active subscription." in content
        assert "Nobody's Plan Anymore" not in content
        assert "9,999.99 GBP" not in content
        assert "every year" not in content
        assert status not in content
        assert str(ended_subscription.current_period_start.year) not in content
        assert "data-mvp-payments-portal-link" not in content

    @pytest.mark.parametrize("status", ["past_due", "unpaid", "incomplete", "paused"])
    def test_a_subscription_needing_attention_is_shown_with_its_status_and_the_portal(
        self, user, client_for, status
    ):
        StripeSubscriptionFactory(
            customer__user=user, status=status, product_name="Needs Attention Plan"
        )

        content = client_for(user).get(reverse("payments:stripe-subscription")).content
        content = content.decode()

        assert "Needs Attention Plan" in content
        assert "data-mvp-payments-portal-link" in content

    def test_a_person_with_no_customer_record_at_all_reaches_the_same_page(
        self, logged_in_client
    ):
        response = logged_in_client.get(reverse("payments:stripe-subscription"))

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
        assert reverse("payments:stripe-billing-portal") in content


class TestPlansPageOverride:
    def test_a_projects_own_page_template_receives_the_plans(self):
        result = run_probe(
            _PLANS_PAGE_TEMPLATE_OVERRIDE_PROBE,
            "tests.settings_with_project_template_override",
        )

        assert result["status_code"] == 200
        content = result["content"]
        assert 'data-testid="the-hosting-projects-own-plans-page"' in content
        assert '<p data-testid="price-id">price_probe</p>' in content
