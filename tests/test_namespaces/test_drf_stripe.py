"""The drf-stripe-subscription namespace's contribution."""

from django.urls import reverse
from django.utils.functional import Promise

from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.markup import account_navigation_regions


class TestDrfStripeContribution:
    """What the namespace declares, and what a signed-in person sees for it."""

    def test_names_the_backends_application_label(self):
        assert drf_stripe.backend_app_name == "drf_stripe"

    def test_declares_exactly_two_pages_with_the_expected_slugs(self):
        assert [page.slug for page in drf_stripe.pages] == ["subscription", "plans"]

    def test_only_the_subscription_page_is_in_the_navigation(self):
        """The plans page is reached from the subscription page, not from the menu."""
        assert [page.slug for page in drf_stripe.pages if page.in_navigation] == [
            "subscription"
        ]

    def test_every_page_label_is_translatable(self):
        assert all(isinstance(page.label, Promise) for page in drf_stripe.pages)

    def test_signed_in_person_sees_one_navigation_entry_per_navigated_page(
        self, logged_in_client
    ):
        content = logged_in_client.get(reverse("account-center")).content.decode()
        # django-mvp draws the Account Center's navigation twice — a collapsed
        # copy above the content and a persistent one beside it — so one entry
        # renders once per region. The assertion stays inside the navigation
        # because the same label also appears on the overview card, which is a
        # different surface with its own tests.
        regions = account_navigation_regions(content)
        assert len(regions) == 2
        for region in regions:
            for page in drf_stripe.pages:
                expected = 1 if page.in_navigation else 0
                assert region.count(f">{page.label}</span>") == expected

    def test_the_pages_sit_under_one_labelled_group(self, logged_in_client):
        """A reader sees a named section, not three loose entries.

        The Account Center is shared with whatever else a project installed,
        so a namespace's pages are grouped under a label of their own the way
        django-accounts-center groups its section of the same menu.
        """
        content = logged_in_client.get(reverse("account-center")).content.decode()

        for region in account_navigation_regions(content):
            assert region.count(">Billing<") == 1
            group_at = region.index(">Billing<")
            for page in drf_stripe.pages:
                if page.in_navigation:
                    assert region.index(f">{page.label}</span>") > group_at
