"""The Stripe app's addresses, included by ``mvp_payments.urls`` when the app is installed."""

from django.urls import path

from .views import webhook

urlpatterns = [
    path("stripe/webhook/", webhook, name="stripe-webhook"),
]
