"""``tests.settings``, plus a project application supplying its own subscription-page template.

Overriding the subscription page's template needs no view, no context processor and no query
of the project's own (FS-002). Proving it needs the project's copy found first, which the
template loader decides from ``INSTALLED_APPS`` order at process start, so a fresh process
starts from this module.
"""

from tests.settings import *  # noqa: F403

INSTALLED_APPS = ["tests.project_app", *INSTALLED_APPS]  # noqa: F405
