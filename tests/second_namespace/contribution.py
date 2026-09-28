"""A second namespace's contribution — a test fixture, not a payment backend.

This package ships exactly one backend (`drf_stripe`), so proving that a
second namespace leaves the first alone (FS-001) needs a stand-in for one: a
minimal installed application (`tests.second_namespace`) to gate on, and a
``Contribution`` declared against it through the exact same public
constructor every real namespace uses. Nothing here is imported by
`mvp_payments/` — the shipped `CONTRIBUTIONS` tuple keeps exactly one entry.
"""

from mvp_payments.contributions import Contribution, Page

second_namespace = Contribution(
    # Nested under `tests.`, so the full dotted name and the short label differ,
    # which is what proves `is_available()` matches the name.
    backend_app_name="tests.second_namespace",
    namespace="second-namespace",
    pages=(
        Page(
            slug="overview",
            label="Second namespace",
            icon="overview",
            template_name="mvp_payments/drf_stripe/subscription.html",
        ),
    ),
    card_template="mvp_payments/card.html",
    group_label="Second payments",
)
