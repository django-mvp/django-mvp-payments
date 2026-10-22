"""SKETCH (FS-005): the public plans page, which a project mounts where it likes.

urlpatterns = [
    path("plans/", include("mvp_payments.plans_urls")),
]
"""

from django.urls import path

from mvp_payments.views import PlansPageView

urlpatterns = [path("", PlansPageView.as_view(), name="stripe-plans")]
