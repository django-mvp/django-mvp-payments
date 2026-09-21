"""``Contribution``: what one namespace puts into the Account Center."""

import pytest
from django.urls import reverse
from mvp_payments.contributions import Contribution, Page


def _make_contribution(app_label="drf_stripe", namespace="fixture-namespace"):
    """A throwaway contribution for exercising the mechanism itself.

    Gated on ``drf_stripe`` by default because that backend is actually
    installed in the test settings, so ``is_available()`` has something real
    to answer against without this package importing it.
    """
    return Contribution(
        backend_app_label=app_label,
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
    def test_registering_twice_renders_each_entry_once(self, logged_in_client):
        from mvp_payments.namespaces.drf_stripe import drf_stripe

        drf_stripe.register()
        drf_stripe.register()

        content = logged_in_client.get(reverse("account-center")).content.decode()
        for page in drf_stripe.pages:
            assert content.count(f"<span>{page.label}</span>") == 1
