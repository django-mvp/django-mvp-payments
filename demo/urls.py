"""The demo project's URL configuration."""

from django.apps import apps
from django.contrib import admin
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
    # Django's admin, where the Stripe app's records can be looked at.
    path("admin/", admin.site.urls),
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
    path("", include("mvp.urls")),
]

if apps.is_installed("drf_stripe"):
    # Only when the backend is installed: its models declare no app_label of their own
    # (tests/settings_without_backend.py). Its own URL configuration is not mounted, because
    # that module imports `stripe.error`, which the Stripe SDK this project runs on has removed.
    # These are the demo's own portal handoffs (demo/views.py says why).
    urlpatterns.append(
        path("api/billing-portal/", BillingPortalView.as_view(), name="billing-portal")
    )
    urlpatterns.append(
        path("api/plan-switch/", PlanSwitchView.as_view(), name="plan-switch")
    )
    urlpatterns.append(
        path(
            "account/billing/return/",
            BillingReturnView.as_view(),
            name="billing-return",
        )
    )
