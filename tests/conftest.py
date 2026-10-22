"""Shared fixtures for the test suite."""

import pytest
from django.test import Client
from django.urls import reverse

from mvp_payments.stripe import client as stripe_client_module
from tests.factories import (
    StripeCustomerFactory,
    StripeSubscriptionFactory,
    StripeUserFactory,
    SubscriptionFactory,
    SubscriptionItemFactory,
    UserFactory,
)
from tests.stripe_fake import FakeStripe


@pytest.fixture
def home_page(client, db):
    return client.get(reverse("home")).content.decode()


@pytest.fixture
def sidebar_navigation(home_page):
    start = home_page.index('aria-label="Main navigation"')
    return home_page[start : home_page.index("</ul>", start)]


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def client_for(db):
    def sign_in(user):
        client = Client()
        client.force_login(user)
        return client

    return sign_in


@pytest.fixture
def logged_in_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def stripe_user(user):
    return StripeUserFactory(user=user)


@pytest.fixture
def current_subscription(stripe_user):
    subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
    SubscriptionItemFactory(subscription=subscription)
    return subscription


@pytest.fixture
def subscriber_client(client, user, current_subscription):
    client.force_login(user)
    return client


@pytest.fixture
def stripe_customer(user):
    return StripeCustomerFactory(user=user)


@pytest.fixture
def stripe_subscription(stripe_customer):
    return StripeSubscriptionFactory(customer=stripe_customer, status="active")


@pytest.fixture
def subscribed_client(client, user, stripe_subscription):
    client.force_login(user)
    return client


@pytest.fixture
def account_center_menu():
    from mvp.menus import AccountCenterMenu

    original = list(AccountCenterMenu.children)
    yield AccountCenterMenu
    AccountCenterMenu.children = original


@pytest.fixture
def stripe_fake(monkeypatch):
    """Stand in for Stripe: the app's own client is built over this HTTP client."""
    fake = FakeStripe()
    monkeypatch.setattr(stripe_client_module, "http_client", fake)
    return fake
