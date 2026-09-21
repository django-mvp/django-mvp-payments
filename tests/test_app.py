"""The package installs and exposes what a consuming project needs from it."""

import json
import os
import subprocess
import sys
from pathlib import Path

from django.apps import apps

import mvp_payments
from mvp_payments.namespaces.drf_stripe import drf_stripe

#: Boots a fresh Django process, signs a person in, opens the Account Center,
#: and reports whether each of the backend's page names reverses. Run as a
#: subprocess because `mvp_payments/urls.py` builds `urlpatterns` once, at
#: import time, and `MvpPaymentsConfig.ready()` registers navigation entries
#: once too — overriding `INSTALLED_APPS` mid-process leaves both exactly as
#: they were built with the backend present, so only a process that never had
#: the backend installed shows what a project without it actually gets.
_ACCOUNT_CENTER_WITHOUT_THE_BACKEND_PROBE = """
import json

import django

django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import NoReverseMatch, reverse

setup_test_environment()
call_command("migrate", verbosity=0, run_syncdb=True)
User.objects.create_user(username="person", password="password")
client = Client()
client.login(username="person", password="password")
response = client.get(reverse("account-center"))

reverses = {}
for name in ("drf-stripe-subscription", "drf-stripe-plans", "drf-stripe-billing"):
    try:
        reverse(f"payments:{name}")
        reverses[name] = True
    except NoReverseMatch:
        reverses[name] = False

print(json.dumps({
    "status_code": response.status_code,
    "content": response.content.decode(),
    "reverses": reverses,
}))
"""


class TestPackagedApp:
    """What a host project gets after installing and adding it to INSTALLED_APPS."""

    def test_app_is_installed(self) -> None:
        assert apps.is_installed("mvp_payments")

    def test_drf_stripe_namespace_is_where_cotton_looks_for_it(self) -> None:
        """Cotton resolves `<c-drf-stripe.plan-grid>` to `cotton/drf_stripe/plan_grid.html`.

        It maps hyphens in a tag name onto underscores on disk, so the directory
        name is not a free choice: renaming it breaks every component tag in the
        namespace at once, and does so silently — a missing component renders as
        empty output rather than raising. The namespace is the payment backend
        rather than this package, so a second backend can be added alongside the
        first without touching it.
        """
        namespace = (
            Path(mvp_payments.__file__).parent / "templates" / "cotton" / "drf_stripe"
        )
        assert namespace.is_dir()

    def test_the_app_defines_no_models(self) -> None:
        """This package owns no table and stores nothing (Article XII).

        Installing it must leave a project's schema untouched, which is also
        why there is no `migrations/` directory for `migrate` to find.
        """
        assert list(apps.get_app_config("mvp_payments").get_models()) == []

    def test_the_package_owns_no_data(self) -> None:
        """No forms, no admin, no serializers, no migrations (Article XII).

        Views, URLs and menu registrations are allowed here — a page has to be
        routed for the package to be worth installing. Accepting a submission,
        exposing a record for editing or defining a wire format is not, because
        each one implies owning data that this package does not have.
        """
        package = Path(mvp_payments.__file__).parent
        forbidden = {"models", "forms", "admin", "serializers", "signals", "migrations"}
        found = sorted(
            str(path.relative_to(package))
            for path in package.rglob("*")
            if path.stem in forbidden and (path.suffix == ".py" or path.is_dir())
        )
        assert found == []

    def test_no_module_reaches_a_database_or_a_provider(self) -> None:
        """The boundary that matters, enforced at the import (Article XII).

        A view here hands a template to the renderer. The moment one imports
        `django.db` it is holding state, and the moment it imports a provider's
        SDK it is moving money — so the imports are what gets asserted, rather
        than a list of filenames that only says what has not been added yet.
        """
        package = Path(mvp_payments.__file__).parent
        banned = ("django.db", "stripe", "paypal", "braintree", "paddle")
        offenders = sorted(
            f"{path.relative_to(package)}: {line.strip()}"
            for path in package.rglob("*.py")
            for line in path.read_text().splitlines()
            if line.startswith(("import ", "from "))
            and any(line.split()[1].startswith(name) for name in banned)
        )
        assert offenders == []

    def test_no_payment_backend_is_a_dependency(self) -> None:
        """Installing this package must never pull a payment backend in.

        The components talk to a backend from the browser, over that backend's
        own HTTP endpoints. Nothing here imports one, which is what lets a
        project swap backends, or run two, without this package having a say.
        """
        import importlib.metadata

        requires = importlib.metadata.requires("django-mvp-payments") or []
        names = {r.split()[0].split("[")[0].split(";")[0].lower() for r in requires}
        assert names == {"django", "django-mvp"}

    def test_the_import_scan_reaches_every_module_this_feature_added(self) -> None:
        """`test_no_module_reaches_a_database_or_a_provider` walks the whole
        package with `rglob`, but a `rglob` call that missed a subdirectory
        would still exit clean — it would just never look there. This pins
        the modules that scan actually visits against the modules this
        feature added, `namespaces/` included, so a future change that
        narrows the walk (a `glob` in place of `rglob`, an early filter) is
        caught here rather than by an import that quietly went unchecked.
        """
        package = Path(mvp_payments.__file__).parent
        scanned = {path.relative_to(package) for path in package.rglob("*.py")}
        added_by_this_feature = {
            Path("apps.py"),
            Path("contributions.py"),
            Path("urls.py"),
            Path("views.py"),
            Path("namespaces/__init__.py"),
            Path("namespaces/drf_stripe.py"),
        }
        assert added_by_this_feature <= scanned


class TestNothingWithoutABackend:
    """A backend that is not installed costs a project nothing (US-2).

    Every check here boots a fresh process under
    `tests.settings_without_backend` rather than overriding `INSTALLED_APPS`
    mid-test — a project that never installed the backend is a process that
    never installed it, and `mvp_payments/urls.py` and
    `MvpPaymentsConfig.ready()` both only build their state once, at that
    process's start.
    """

    def _open_the_account_center_without_the_backend(self) -> dict:
        # sys.executable and a module-level string constant, no untrusted input.
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-c", _ACCOUNT_CENTER_WITHOUT_THE_BACKEND_PROBE],
            env={
                **os.environ,
                "DJANGO_SETTINGS_MODULE": "tests.settings_without_backend",
            },
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout.strip().splitlines()[-1])

    def test_account_center_shows_nothing_from_the_absent_backend(self) -> None:
        result = self._open_the_account_center_without_the_backend()

        # The page itself still renders, with its own navigation intact — a
        # missing backend is not a broken page.
        assert result["status_code"] == 200
        assert 'aria-label="Account navigation"' in result["content"]

        # No navigation entry and no card: both render the page's label, so
        # one absence check covers both surfaces (there is no card template
        # to render yet — that is US-3 — which is why this also holds today).
        for page in drf_stripe.pages:
            assert f"<span>{page.label}</span>" not in result["content"]

        # None of the backend's page addresses resolve.
        assert result["reverses"] == {
            "drf-stripe-subscription": False,
            "drf-stripe-plans": False,
            "drf-stripe-billing": False,
        }

    def test_account_center_shows_no_card_from_the_absent_backend(self) -> None:
        # US-3's carried-forward item: the check above predates the card
        # template (mvp_payments/templates/mvp_payments/card.html), so it
        # could only ever assert against navigation markup. Now that the
        # template exists, re-prove the absence against its own markup — the
        # link a card would carry into the backend's first page.
        result = self._open_the_account_center_without_the_backend()

        assert 'href="/payments/drf-stripe/subscription/"' not in result["content"]
