from django.urls import path

from demo.views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]
