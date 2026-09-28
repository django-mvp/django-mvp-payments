"""``tests.settings``, plus the second namespace's own installed application.

A namespace is available only once its backend's application is installed, and
the URLs and navigation entries are built once at startup (see
`settings_without_backend`), so a fresh process starts from this module.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "tests.second_namespace"]  # noqa: F405
