"""The Stripe namespace's contribution."""

from django.urls import reverse
from django.utils.functional import Promise

from mvp_payments.namespaces.stripe import stripe_contribution
from tests.markup import account_navigation_regions


class TestStripeContribution:
    def test_names_the_backends_application_label(self):
        assert stripe_contribution.backend_app_name == "mvp_payments.stripe"

    def test_declares_exactly_one_page_with_the_expected_slug(self):
        assert [page.slug for page in stripe_contribution.pages] == ["subscription"]

    def test_every_page_label_is_translatable(self):
        assert all(
            isinstance(page.label, Promise) for page in stripe_contribution.pages
        )

    def test_signed_in_person_sees_one_navigation_entry_per_page(
        self, logged_in_client
    ):
        content = logged_in_client.get(reverse("account-center")).content.decode()
        # Counting inside the navigation keeps the overview card out.
        regions = account_navigation_regions(content)
        assert len(regions) == 1
        for region in regions:
            for page in stripe_contribution.pages:
                assert region.count(f">{page.label}</span>") == 1

    def test_the_pages_sit_under_one_labelled_group(self, logged_in_client):
        content = logged_in_client.get(reverse("account-center")).content.decode()

        regions = account_navigation_regions(content)
        assert len(regions) == 1
        for region in regions:
            group = f">{stripe_contribution.group_label}<"
            assert region.count(group) == 1
            group_at = region.index(group)
            for page in stripe_contribution.pages:
                assert region.index(f">{page.label}</span>") > group_at
