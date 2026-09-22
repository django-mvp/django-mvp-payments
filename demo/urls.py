from django.apps import apps
from django.urls import include, path

from demo.views import HomeView, NoLibraryView, PlansUnconfiguredView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # US-4 scenarios 1, 2 and 3: neither value configured, and the library
    # never having arrived — both the demonstration project's own routes.
    path(
        "plans-unconfigured/",
        PlansUnconfiguredView.as_view(),
        name="plans-unconfigured",
    ),
    path("no-library/", NoLibraryView.as_view(), name="no-library"),
    # The Account Center is django-mvp's, and this package contributes pages to
    # it. A project mounts it once; so does this demo.
    path("account/", include("mvp.urls")),
    # Every page this package contributes requires a signed-in person, so the
    # demo needs somewhere to sign in.
    path("accounts/", include("django.contrib.auth.urls")),
    # The one line a project adds to mount this package's pages (FR-001).
    path("payments/", include("mvp_payments.urls")),
]

if apps.is_installed("drf_stripe"):
    # The backend's own API, including its billing-portal endpoint. Its
    # location is the demo's decision — MVP_PAYMENTS['DRF_STRIPE_BILLING_PORTAL']
    # in settings.py is where this project told the page it mounted it (D3,
    # FR-006). Conditional on the backend being installed, the way a real
    # project's own URLconf naturally would be — tests/settings_without_backend.py
    # removes it from INSTALLED_APPS, and importing its URLconf regardless
    # raises before the module even loads (its models declare no app_label
    # of their own to fall back on).
    urlpatterns.append(path("api/stripe/", include("drf_stripe.urls")))
