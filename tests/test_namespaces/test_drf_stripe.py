"""The drf-stripe-subscription namespace's contribution."""

from django.urls import reverse
from django.utils.functional import Promise

from mvp_payments.namespaces.drf_stripe import drf_stripe


class TestDrfStripeContribution:
    """What the namespace declares, and what a signed-in person sees for it."""

    def test_names_the_backends_application_label(self):
        assert drf_stripe.backend_app_label == "drf_stripe"

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
        # mvp/account/base.html draws AccountCenterMenu twice — a collapsed
        # mobile dropdown copy and a persistent desktop card — so one
        # registered entry legitimately appears twice in the rendered page.
        for page in drf_stripe.pages:
            assert content.count(f"<span>{page.label}</span>") == 2
