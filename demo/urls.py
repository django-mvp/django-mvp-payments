"""The demo project's URL configuration."""

from django.contrib import admin
from django.urls import include, path

from demo.views import HomeView, NoLibraryView, PlansUnconfiguredView

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
