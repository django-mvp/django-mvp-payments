"""A second namespace's contribution — a test fixture, not a payment backend.

This package ships exactly one backend (`drf_stripe`), so proving that a
second namespace leaves the first alone (US-5) needs a stand-in for one: a
minimal installed application (`tests.second_namespace`) to gate on, and a
``Contribution`` declared against it through the exact same public
constructor every real namespace uses. Nothing here is imported by
`mvp_payments/` — the shipped `CONTRIBUTIONS` tuple keeps exactly one entry.
"""

from mvp_payments.contributions import Contribution, Page

second_namespace = Contribution(
    # `Contribution.is_available()` passes this straight to Django's
    # `apps.is_installed()`, which checks it against each installed app's
    # full dotted *name* (`AppConfig.name`), not its short *label* — despite
    # the field being named for the label. The shipped namespace's backend
    # happens to be installed at the top level, where the two coincide; this
    # fixture is nested under `tests.`, where they do not, which is what
    # exposes the mismatch.
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
)
