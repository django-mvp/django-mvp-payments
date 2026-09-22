"""Rendering a contributed page inside the Account Center layout."""

import re

import pytest
from django.conf import settings
from django.db import connection
from django.test import Client, override_settings
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


class TestPaymentPage:
    """A signed-in request renders; an anonymous one is sent to sign in."""

    @pytest.mark.parametrize(
        ("url_name", "heading"),
        [
            ("drf-stripe-subscription", "Subscription"),
            ("drf-stripe-plans", "Plans"),
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


class TestPageViewConfiguration:
    """A view built without what it needs says so, rather than failing later."""

    def test_a_view_with_no_contribution_says_what_is_missing(self):
        """Every route supplies one, so this fires only for a hand-built view.

        It is the difference between a clear message at the point of the
        mistake and an ``AttributeError`` on ``None`` somewhere inside a
        template render.
        """
        from django.core.exceptions import ImproperlyConfigured

        from mvp_payments.views import SubscriptionPageView

        with pytest.raises(ImproperlyConfigured, match="requires `contribution`"):
            SubscriptionPageView().get_contribution()


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
            assert ">Billing<" not in region

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

    def test_the_portal_control_offers_to_manage_the_subscription(
        self, subscriber_client
    ):
        """The control names what it manages, now that no page is named for it."""
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert "Manage subscription" in content
        assert "Manage billing" not in content

    def test_both_ways_onward_sit_in_one_row(self, subscriber_client):
        """Stacked, they read as two unrelated things; side by side, as a choice.

        Asserted structurally rather than by class name: both controls are
        inside the same container, in the order the page declares them.
        """
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        row = re.search(
            r"<div[^>]*data-mvp-payments-subscription-actions[^>]*>(.*?)</div>\s*</div>",
            content,
            re.S,
        )
        assert row is not None
        assert "Switch plans" in row.group(1)
        assert "data-mvp-payments-portal-link" in row.group(1)
        assert row.group(1).index("Switch plans") < row.group(1).index(
            "data-mvp-payments-portal-link"
        )

    def test_a_subscriber_is_offered_the_way_to_switch_plans(self, subscriber_client):
        """The plans page left the navigation, so this control is how it is reached."""
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert f'href="{reverse("payments:drf-stripe-plans")}"' in content
        assert "Switch plans" in content

    def test_someone_with_no_subscription_is_invited_to_choose_one(self, user):
        """ "Switch plans" reads wrong to somebody who is not on one yet."""
        client = self._client_for(user)

        response = client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert f'href="{reverse("payments:drf-stripe-plans")}"' in content
        assert "Choose a plan" in content
        assert "Switch plans" not in content

    def test_the_portal_control_carries_a_usable_csrf_token(self, subscriber_client):
        """Empty here and the control posts a request Django rejects, every time.

        The component reads the token from context rather than from an attribute, so
        this is the assertion that the dependency is actually satisfied on a real page.
        """
        response = subscriber_client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        token = re.search(r'data-csrf-token="([^"]*)"', content)
        assert token is not None
        assert len(token.group(1)) > 20

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


@pytest.mark.django_db
class TestNoCurrentSubscription:
    """Nobody the backend reports nothing current for is left with a hole where a plan
    would have been (T025, US-4, FR-008, D5, D11).

    Two different people reach this with nothing: one the backend holds no customer
    record for at all, and one whose subscriptions exist but none of them are current.
    ``SubscriptionReader.for_user`` returns an empty tuple for both, so the page reads
    the same way for each — this class proves that for both paths, not only one.
    """

    def test_a_person_whose_subscription_has_ended_is_told_there_is_none(self, user):
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

        client = self._client_for(user)
        response = client.get(reverse("payments:drf-stripe-subscription"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "No current subscription" in content
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
        assert "No current subscription" in content
        assert "data-mvp-payments-portal-link" not in content

    def _client_for(self, user):
        client = Client()
        client.force_login(user)
        return client


class TestTemplateOverride:
    """A project's own template, found before this package's, renders every value the
    shipped page had — with no view, no context processor and no query of its own (T028,
    FR-011, SC-005).

    The app-directories template loader decides which application's copy of a name wins
    from ``INSTALLED_APPS`` order, fixed at process start (D4, 001-pages-arrive-on-install) —
    the same reason ``TestAccountCenterOverview`` above boots a fresh process rather than
    reordering ``INSTALLED_APPS`` mid-test.
    """

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
