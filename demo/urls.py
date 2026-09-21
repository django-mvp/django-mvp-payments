from django.urls import include, path

from demo.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # The Account Center is django-mvp's, and this package contributes pages to
    # it. A project mounts it once; so does this demo.
    path("account/", include("mvp.urls")),
    # Every page this package contributes requires a signed-in person, so the
    # demo needs somewhere to sign in.
    path("accounts/", include("django.contrib.auth.urls")),
    # The one line a project adds to mount this package's pages (FR-001).
    path("payments/", include("mvp_payments.urls")),
]
