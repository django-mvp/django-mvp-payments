"""The demo's routes with the plans page's include removed.

Mirrors ``demo/urls.py`` minus the one line a project adds to offer the plans page: a project
that mounted the Account Center's pages and never mounted the plans.
"""

from django.urls import include, path

from demo.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("account/billing/", include("mvp_payments.urls")),
    path("", include("mvp.urls")),
]
