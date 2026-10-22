"""The public plans page, which a project mounts where it likes.

A project includes this once, at the address it chooses, beside the single include of
``mvp_payments.urls``::

    urlpatterns = [
        path("plans/", include("mvp_payments.plans_urls")),
    ]

The page is routed only while the Stripe app is installed, as ``payments_plans:stripe-plans``.
"""

from django.apps import apps
from django.urls import URLPattern, path

from mvp_payments.views import PlansPageView

app_name = "payments_plans"

urlpatterns: list[URLPattern] = []

if apps.is_installed("mvp_payments.stripe"):
    urlpatterns.append(path("", PlansPageView.as_view(), name="stripe-plans"))
