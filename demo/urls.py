from django.urls import path

from demo.views import LandingView

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
]
