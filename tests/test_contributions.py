"""``Contribution``: what one namespace puts into the Account Center."""

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from mvp_payments.contributions import Contribution, Page
from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.markup import account_navigation_regions
from tests.probes import run_probe
from tests.second_namespace.contribution import second_namespace


def _make_contribution(app_label="drf_stripe", namespace="fixture-namespace"):
    """A throwaway contribution for exercising the mechanism itself.

    Gated on ``drf_stripe`` by default because that backend is actually
    installed in the test settings, so ``is_available()`` has something real
    to answer against without this package importing it.
    """
    return Contribution(
        backend_app_name=app_label,
        namespace=namespace,
        pages=(
            Page(
                slug="one",
                label="One",
                icon="overview",
                template_name="mvp_payments/drf_stripe/subscription.html",
            ),
            Page(
                slug="two",
                label="Two",
                icon="overview",
                template_name="mvp_payments/drf_stripe/plans.html",
            ),
        ),
        card_template="mvp_payments/card.html",
    )


class TestContribution:
    """Availability, routing and registration — the mechanism every namespace shares."""

    def test_reports_available_when_its_backend_is_installed(self):
        assert _make_contribution(app_label="drf_stripe").is_available() is True

    def test_reports_unavailable_when_its_backend_is_not_installed(self):
        assert (
            _make_contribution(app_label="not_an_installed_app").is_available() is False
        )

    def test_url_patterns_returns_one_route_per_declared_page(self):
        contribution = _make_contribution(namespace="url-patterns-fixture")
        patterns = contribution.url_patterns()
        assert len(patterns) == 2
        assert {pattern.name for pattern in patterns} == {
            "url-patterns-fixture-one",
            "url-patterns-fixture-two",
        }

    def test_register_adds_exactly_one_navigation_entry_per_page(
        self, account_center_menu
    ):
        contribution = _make_contribution(namespace="register-count-fixture")
        before = len(account_center_menu.children)

        contribution.register()

        after = list(account_center_menu.children)
        assert len(after) - before == len(contribution.pages)
        assert {child.name for child in after[-2:]} == {
            "register-count-fixture-one",
            "register-count-fixture-two",
        }


class TestRepeatedRegistration:
    """``ready()`` runs again on every development-server reload."""

    @pytest.mark.django_db
    def test_registering_twice_does_not_duplicate_entries(self, logged_in_client):
        from mvp_payments.namespaces.drf_stripe import drf_stripe

        drf_stripe.register()
        drf_stripe.register()

        content = logged_in_client.get(reverse("account-center")).content.decode()
        # django-mvp draws the Account Center's navigation twice — a collapsed
        # copy above the content and a persistent one beside it — so one
        # registered entry renders once in each region and nowhere else in
        # them. Counting inside the navigation rather than across the page
        # keeps this about registration: the same label also appears on the
        # overview card, which is a different surface with its own tests.
        regions = account_navigation_regions(content)
        assert len(regions) == 2
        for region in regions:
            for page in drf_stripe.pages:
                assert (
                    region.count(
                        f'href="{reverse(f"payments:drf-stripe-{page.slug}")}"'
                    )
                    == 1
                )


class TestSecondNamespaceFixture:
    """The fixture that stands in for a second payment backend (US-5).

    Proves `tests/second_namespace/` registers through exactly the same
    public mechanism every real namespace uses — `is_available()` and
    `register()`, called the same way `TestContribution` above calls them on
    a throwaway contribution — with no special case anywhere in
    `mvp_payments/`.
    """

    def test_reports_unavailable_before_its_app_is_installed(self):
        assert second_namespace.is_available() is False

    def test_registers_through_the_same_mechanism_as_the_shipped_namespace(
        self, account_center_menu
    ):
        with override_settings(
            INSTALLED_APPS=[*settings.INSTALLED_APPS, "tests.second_namespace"]
        ):
            assert second_namespace.is_available() is True
            before = len(account_center_menu.children)
            second_namespace.register()
            after = list(account_center_menu.children)

        assert len(after) - before == len(second_namespace.pages)
        assert {child.name for child in after[-1:]} == {"second-namespace-overview"}


#: Boots a fresh Django process with the second namespace's fixture app added
#: to `CONTRIBUTIONS` for that process only (D1), signs a person in, opens
#: the Account Center, and reports the rendered page plus every page
#: address's resolved path. Run as a subprocess for the same reason D9 and
#: D10 do: `mvp_payments/urls.py` builds `urlpatterns` once, at import time,
#: and `MvpPaymentsConfig.ready()` registers navigation entries once, at
#: startup — patching `CONTRIBUTIONS` after either has already run would
#: leave both exactly as first built. Patching before the first `reverse()`
#: call and re-running the same `ready()` Django already called once (exactly
#: what an autoreloading dev server does, per D5) is enough, so no fresh
#: settings module is needed for the fixture itself — only for whether its
#: application is actually installed.
_NAMESPACE_INDEPENDENCE_PROBE = """
import json

import django

django.setup()

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import NoReverseMatch, reverse

import mvp_payments.namespaces as namespaces
from tests.second_namespace.contribution import second_namespace

namespaces.CONTRIBUTIONS = namespaces.CONTRIBUTIONS + (second_namespace,)
apps.get_app_config("mvp_payments").ready()

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)
User.objects.create_user(username="person", password="password")
client = Client()
client.login(username="person", password="password")
response = client.get(reverse("account-center"))

reverses = {}
for name in (
    "payments:drf-stripe-subscription",
    "payments:drf-stripe-plans",
    "payments:drf-stripe-billing",
    "payments:second-namespace-overview",
):
    try:
        reverses[name] = reverse(name)
    except NoReverseMatch:
        reverses[name] = None

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
    "reverses": reverses,
}))
"""


class TestNamespaceIndependence:
    """A second namespace leaves the first exactly as it was (US-5).

    Both runs boot a fresh process rather than using `override_settings`
    mid-test (D9/D10's shape): the first namespace's page addresses,
    navigation and card are all built once, at import or startup, so only a
    process that starts with the fixture actually installed shows what a
    project with a second namespace gets.
    """

    def _open_the_account_center(self, settings_module: str) -> dict:
        # sys.executable and a module-level string constant, no untrusted input.
        return run_probe(_NAMESPACE_INDEPENDENCE_PROBE, settings_module)

    def test_the_first_namespaces_entries_card_and_pages_are_unchanged(self) -> None:
        alone = self._open_the_account_center("tests.settings")
        alongside = self._open_the_account_center(
            "tests.settings_with_second_namespace"
        )

        for page in drf_stripe.pages:
            marker = f"<span>{page.label}</span>"
            assert alongside["content"].count(marker) == alone["content"].count(marker)

        card_href = 'href="/payments/drf-stripe/subscription/"'
        assert card_href in alone["content"]
        assert card_href in alongside["content"]

        for name in (
            "payments:drf-stripe-subscription",
            "payments:drf-stripe-plans",
            "payments:drf-stripe-billing",
        ):
            assert alongside["reverses"][name] == alone["reverses"][name]

    def test_neither_namespaces_pages_resolve_to_the_others(self) -> None:
        alongside = self._open_the_account_center(
            "tests.settings_with_second_namespace"
        )
        addresses = list(alongside["reverses"].values())
        assert None not in addresses
        assert len(addresses) == len(set(addresses))

    def test_no_two_declared_contributions_share_a_url_name(self) -> None:
        names = [
            pattern.name
            for contribution in (drf_stripe, second_namespace)
            for pattern in contribution.url_patterns()
        ]
        assert len(names) == len(set(names))
