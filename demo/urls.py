"""The demo project's URL configuration."""

from django.apps import apps
from django.urls import include, path

from demo.views import (
    BillingPortalView,
    BillingReturnView,
    HomeView,
    NoLibraryView,
    PlansUnconfiguredView,
    PlanSwitchView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # The plans page's unavailable states, as the demonstration project's own routes (FS-003).
    path(
        "plans-unconfigured/",
        PlansUnconfiguredView.as_view(),
        name="plans-unconfigured",
    ),
    path("no-library/", NoLibraryView.as_view(), name="no-library"),
    # The one line a project adds. Declared before the Account Center's include, so
    # this prefix matches here rather than relying on `mvp.urls` declining it.
    path("account/billing/", include("mvp_payments.urls")),
    path("account/", include("mvp.urls")),
]

if apps.is_installed("drf_stripe"):
    # Only when the backend is installed: importing its URLconf otherwise raises, because
    # its models declare no app_label of their own (tests/settings_without_backend.py).
    urlpatterns.append(path("api/stripe/", include("drf_stripe.urls")))
    # The demo's own portal handoff, which the page uses instead of the backend's
    # (demo/views.py says why), mounted beside the backend's rather than over it.
    urlpatterns.append(
        path("api/billing-portal/", BillingPortalView.as_view(), name="billing-portal")
    )
    urlpatterns.append(
        path("api/plan-switch/", PlanSwitchView.as_view(), name="plan-switch")
    )
    urlpatterns.append(
        path("billing/return/", BillingReturnView.as_view(), name="billing-return")
    )
