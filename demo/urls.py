"""The demo project's URL configuration."""

from django.contrib import admin
from django.urls import include, path

from demo.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # Django's admin, where the Stripe app's records can be looked at.
    path("admin/", admin.site.urls),
    # The one line a project adds. Declared before the Account Center's include, so
    # this prefix matches here rather than relying on `mvp.urls` declining it.
    path("account/billing/", include("mvp_payments.urls")),
    # The public plans page, at the address the project chooses (FS-005).
    path("plans/", include("mvp_payments.plans_urls")),
    path("", include("mvp.urls")),
]
