"""The demo's routes with this package's include removed.

Mirrors ``demo/urls.py`` exactly, minus the one line a project adds to mount
this package's pages (FR-001) — the state US-4 tests: a project that
installed the backend and this package but never added that line.
"""

from django.urls import include, path

from demo.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("account/", include("mvp.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]
