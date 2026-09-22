from django.apps import apps
from django.urls import include, path

from demo.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # The one line a project adds to mount this package's pages (FR-001).
    # Mounted inside the Account Center's own prefix, under the label the
    # navigation uses, so the address bar agrees with where a reader thinks
    # they are. Declared before the Account Center's own include so that this
    # prefix is matched here rather than depending on `mvp.urls` declining it.
    path("account/billing/", include("mvp_payments.urls")),
    # The Account Center is django-mvp's, and this package contributes pages to
    # it. A project mounts it once; so does this demo.
    path("account/", include("mvp.urls")),
    # Every page this package contributes requires a signed-in person, so the
    # demo needs somewhere to sign in.
    path("accounts/", include("django.contrib.auth.urls")),
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
