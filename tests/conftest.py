"""Shared fixtures for the test suite."""

import pytest
from django.urls import reverse


@pytest.fixture
def home_page(client, db):
    """The demo project's home page, rendered, as a string."""
    return client.get(reverse("home")).content.decode()


@pytest.fixture
def sidebar_navigation(home_page):
    """Just the sidebar's navigation list, cut out of the rendered page."""
    start = home_page.index('aria-label="Main navigation"')
    return home_page[start : home_page.index("</ul>", start)]
