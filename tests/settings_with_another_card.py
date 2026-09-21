"""``tests.settings``, plus a second application that also contributes a card.

Proving that ``{{ block.super }}`` was kept in this package's override of
``mvp/account/overview.html`` needs a second application in the extends
chain. Django resolves that chain from ``INSTALLED_APPS`` order once, at
process start, the same way it builds the URL configuration and the Account
Center's navigation (see ``settings_without_backend``) — so this is a
distinct settings module a fresh process starts from, not a setting
overridden mid-test.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = [
    *INSTALLED_APPS[: INSTALLED_APPS.index("mvp")],  # noqa: F405
    "tests.other_app",
    *INSTALLED_APPS[INSTALLED_APPS.index("mvp") :],  # noqa: F405
]
