"""The drf-stripe-subscription namespace's contribution."""

from django.urls import reverse
from django.utils.functional import Promise

from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.markup import account_navigation_regions


class TestDrfStripeContribution:
    """What the namespace declares, and what a signed-in person sees for it."""

    def test_names_the_backends_application_label(self):
        assert drf_stripe.backend_app_name == "drf_stripe"

    def test_declares_exactly_three_pages_with_the_expected_slugs(self):
        assert [page.slug for page in drf_stripe.pages] == [
            "subscription",
            "plans",
            "billing",
        ]

    def test_every_page_label_is_translatable(self):
        assert all(isinstance(page.label, Promise) for page in drf_stripe.pages)

    def test_signed_in_person_sees_one_navigation_entry_per_page(
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
                assert region.count(f">{page.label}</span>") == 1
