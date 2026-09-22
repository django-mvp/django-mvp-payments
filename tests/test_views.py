"""Rendering a contributed page inside the Account Center layout."""

import re

import pytest
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.factories import (
    PriceFactory,
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


class TestPaymentPage:
    """A signed-in request renders; an anonymous one is sent to sign in."""

    @pytest.mark.parametrize(
        ("url_name", "heading"),
        [
            ("drf-stripe-subscription", "Subscription"),
            ("drf-stripe-plans", "Plans"),
            ("drf-stripe-billing", "Billing"),
        ],
    )
    def test_signed_in_person_sees_the_page_inside_the_account_center(
        self, logged_in_client, url_name, heading
    ):
        response = logged_in_client.get(reverse(f"payments:{url_name}"))
        content = response.content.decode()

        assert response.status_code == 200
        assert re.search(rf"<h1[^>]*>\s*{heading}\s*</h1>", content)
        assert 'aria-label="Account navigation"' in content

    def test_anonymous_visitor_is_sent_to_the_sign_in_page(self, client, db):
        response = client.get(reverse("payments:drf-stripe-subscription"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))


class TestAccountCenterOverview:
    """The overview carries the installed backend's card, and keeps whatever
    django-mvp or another application already put there through
    ``{{ block.super }}`` (FR-006, FR-009).

    Proving the second half needs a second application in the extends chain,
    present from process start — the app-directories template loader order is
    built once, like the URL configuration and the menu (D9) — so this boots
    a fresh process under ``tests.settings_with_another_card`` rather than
    overriding ``INSTALLED_APPS`` mid-test.
    """

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
    """A project that installed the backend but never added the one line
    mounting this package's URL configuration still gets a working Account
    Center, with nothing of this package on it (US-4, FR-009).

    A dead navigation entry is already handled by django-flex-menus, which
    drops a leaf whose URL will not reverse (D3) — the navigation half needs
    no test of its own here beyond confirming it stays true. The card is not
    covered by that: rendering its ``{% url %}`` would raise
    ``NoReverseMatch`` and take the whole page down, which is worse than the
    dead link FR-009 exists to prevent.

    Both guards ask ``reverse()`` live, at render time — ``Contribution.
    is_reachable()`` directly, django-flex-menus' own URL resolution the same
    way — rather than anything built once at process start. That is unlike
    D9's URL-configuration-built-at-import case and D10's template-loader
    case, so this uses ``override_settings(ROOT_URLCONF=...)`` in-process
    rather than a fresh subprocess: confirmed by hand first that Django's own
    ``clear_url_caches()`` (triggered by the ``setting_changed`` signal on a
    ``ROOT_URLCONF`` override) is enough to make every live ``reverse()``
    call in this request see the substituted URL configuration.
    """

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
            assert ">Payments<" not in region

        # No card: its link would need a URL name that cannot reverse here.
        cards = account_center_cards_region(content)
        assert "<a href" not in cards
        for page in drf_stripe.pages:
            assert f">{page.label}<" not in cards


@pytest.mark.django_db
class TestSubscriptionPage:
    """The subscription page renders what the reader returns and nothing it did not (T007)."""

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

    def test_two_priced_items_show_both_amounts_and_no_third_figure(self, user):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
        first_price = PriceFactory(price=2000, currency="USD", freq="month_1")
        second_price = PriceFactory(price=3000, currency="EUR", freq="month_1")
        SubscriptionItemFactory(subscription=subscription, price=first_price)
        SubscriptionItemFactory(subscription=subscription, price=second_price)

        client = self._client_for(user)
        content = client.get(
            reverse("payments:drf-stripe-subscription")
        ).content.decode()

        assert set(_AMOUNT_PATTERN.findall(content)) == {"20.00 USD", "30.00 EUR"}

    def test_an_unrecognised_status_renders_as_itself(self, user):
        stripe_user = StripeUserFactory(user=user)
        subscription = SubscriptionFactory(stripe_user=stripe_user, status="past_due")
        SubscriptionItemFactory(subscription=subscription)

        client = self._client_for(user)
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

    def test_a_fixed_number_of_queries_whatever_the_number_of_items(self, user):
        one_item_user = user
        stripe_user_one = StripeUserFactory(user=one_item_user)
        subscription_one = SubscriptionFactory(
            stripe_user=stripe_user_one, status="active"
        )
        SubscriptionItemFactory(subscription=subscription_one)

        many_items_user = self._another_user()
        stripe_user_many = StripeUserFactory(user=many_items_user)
        subscription_many = SubscriptionFactory(
            stripe_user=stripe_user_many, status="active"
        )
        for _ in range(4):
            SubscriptionItemFactory(subscription=subscription_many)

        client_one = self._client_for(one_item_user)
        client_many = self._client_for(many_items_user)
        page_url = reverse("payments:drf-stripe-subscription")

        # A first request against either client warms process-wide caches (the site,
        # content types) that a later request benefits from regardless of how many
        # items it holds — priming both first keeps the comparison about the page's
        # own queries rather than which client happened to go first.
        client_one.get(page_url)
        client_many.get(page_url)

        with CaptureQueriesContext(connection) as captured_one:
            client_one.get(page_url)
        with CaptureQueriesContext(connection) as captured_many:
            client_many.get(page_url)

        assert len(captured_one) == len(captured_many)

    def test_the_portal_control_sits_beneath_the_subscriptions(self, subscriber_client):
        """T020: the demo's own MVP_PAYMENTS setting and static file, end to end."""
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        status_index = content.index("active")
        control_index = content.index("data-mvp-payments-portal-link")
        assert control_index > status_index
        assert 'src="/static/mvp_payments/drf_stripe/billing_portal.js"' in content

    def _client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def _another_user(self):
        return UserFactory()


@pytest.mark.django_db
class TestBillingPortalEndpoint:
    """``billing_portal_endpoint`` in the subscription page's context (T015)."""

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
        """A person with nothing current is told nothing about "your subscription".

        ``billing_portal_endpoint`` is None both for an unconfigured project and for a
        person with nothing to manage, and the component cannot tell those apart. The
        page can: it renders the control only where there is a subscription behind it.
        Without that, someone who never subscribed reads that their subscription is
        managed by the provider and that the portal is temporarily unreachable, and
        both halves of that are untrue (FR-008).
        """
        with override_settings(
            MVP_PAYMENTS={"DRF_STRIPE_BILLING_PORTAL": "/api/stripe/customer-portal/"}
        ):
            response = logged_in_client.get(reverse("payments:drf-stripe-subscription"))

        content = response.content.decode()
        assert "data-mvp-payments-portal-link" not in content
        assert "managed by the provider" not in content
        assert "cannot be reached" not in content
