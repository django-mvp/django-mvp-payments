"""Shared fixtures for the test suite."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from tests.factories import (
    StripeUserFactory,
    SubscriptionFactory,
    SubscriptionItemFactory,
)


@pytest.fixture
def home_page(client, db):
    """The demo project's home page, rendered, as a string."""
    return client.get(reverse("home")).content.decode()


@pytest.fixture
def sidebar_navigation(home_page):
    """Just the sidebar's navigation list, cut out of the rendered page."""
    start = home_page.index('aria-label="Main navigation"')
    return home_page[start : home_page.index("</ul>", start)]


@pytest.fixture
def user(db):
    """A signed-in person, for the pages that require one."""
    return User.objects.create_user(username="person", password="password")


@pytest.fixture
def logged_in_client(client, user):
    """A test client already signed in as ``user``."""
    client.force_login(user)
    return client


@pytest.fixture
def stripe_user(user):
    """The backend's record of ``user`` as a Stripe customer."""
    return StripeUserFactory(user=user)


@pytest.fixture
def current_subscription(stripe_user):
    """One active subscription covering one priced item of a product."""
    subscription = SubscriptionFactory(stripe_user=stripe_user, status="active")
    SubscriptionItemFactory(subscription=subscription)
    return subscription


@pytest.fixture
def subscriber_client(client, user, current_subscription):
    """A signed-in client whose person holds ``current_subscription``."""
    client.force_login(user)
    return client


@pytest.fixture
def account_center_menu():
    """A handle on the Account Center's navigation tree that restores itself.

    ``register()`` mutates ``AccountCenterMenu`` in place — a process-wide
    singleton — so a test that registers a throwaway contribution into it
    restores the tree afterwards rather than leaking entries into later tests.
    """
    from mvp.menus import AccountCenterMenu

    original = list(AccountCenterMenu.children)
    yield AccountCenterMenu
    AccountCenterMenu.children = original
