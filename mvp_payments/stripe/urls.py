"""The Stripe app's addresses, included by ``mvp_payments.urls`` when the app is installed."""

from django.urls import path

from .views import BillingPortalView, BillingReturnView, PlanSwitchView, webhook

urlpatterns = [
    path("stripe/webhook/", webhook, name="stripe-webhook"),
    path(
        "stripe/billing-portal/",
        BillingPortalView.as_view(),
        name="stripe-billing-portal",
    ),
    path("stripe/plan-switch/", PlanSwitchView.as_view(), name="stripe-plan-switch"),
    path("stripe/return/", BillingReturnView.as_view(), name="stripe-billing-return"),
]
