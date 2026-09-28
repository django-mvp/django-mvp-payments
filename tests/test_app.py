"""The package installs and exposes what a consuming project needs from it."""

import re
from pathlib import Path

from django.apps import apps

import mvp_payments
from mvp_payments.namespaces.drf_stripe import drf_stripe
from tests.probes import run_probe

_SCRIPT_WITH_HOST_SRC = re.compile(
    r"""<script[^>]*\bsrc\s*=\s*['"](?:https?:)?//""", re.IGNORECASE
)

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
for name in ("drf-stripe-subscription", "drf-stripe-plans"):
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
    def test_app_is_installed(self) -> None:
        assert apps.is_installed("mvp_payments")

    def test_drf_stripe_namespace_is_where_cotton_looks_for_it(self) -> None:
        namespace = (
            Path(mvp_payments.__file__).parent / "templates" / "cotton" / "drf_stripe"
        )
        assert namespace.is_dir()

    def test_the_app_defines_no_models(self) -> None:
        assert list(apps.get_app_config("mvp_payments").get_models()) == []

    def test_the_package_owns_no_data(self) -> None:
        package = Path(mvp_payments.__file__).parent
        forbidden = {"models", "forms", "admin", "serializers", "signals", "migrations"}
        found = sorted(
            str(path.relative_to(package))
            for path in package.rglob("*")
            if path.stem in forbidden and (path.suffix == ".py" or path.is_dir())
        )
        assert found == []

    def test_no_module_reaches_a_database_or_a_provider(self) -> None:
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
        import importlib.metadata

        from packaging.requirements import Requirement

        requires = importlib.metadata.requires("django-mvp-payments") or []
        names = {Requirement(r).name.lower() for r in requires}
        assert names == {"django", "django-mvp"}

    def test_the_import_scan_reaches_every_module_this_feature_added(self) -> None:
        package = Path(mvp_payments.__file__).parent
        scanned = {path.relative_to(package) for path in package.rglob("*.py")}
        added_by_this_feature = {
            Path("apps.py"),
            Path("contributions.py"),
            Path("urls.py"),
            Path("views.py"),
            Path("namespaces/__init__.py"),
            Path("namespaces/drf_stripe.py"),
            Path("templatetags/__init__.py"),
            Path("templatetags/mvp_payments.py"),
        }
        assert added_by_this_feature <= scanned


class TestDocumentationLinkedFromReadme:
    def test_the_plans_page_documentation_is_linked(self) -> None:
        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text()
        assert "[docs/plans-page.md](docs/plans-page.md)" in readme


class TestNoProviderScript:
    def test_no_shipped_template_contains_a_script_element_with_a_host_src(
        self,
    ) -> None:
        package = Path(mvp_payments.__file__).parent / "templates"
        offenders = sorted(
            str(path.relative_to(package))
            for path in package.rglob("*.html")
            if _SCRIPT_WITH_HOST_SRC.search(path.read_text())
        )
        assert offenders == []


class TestNothingWithoutABackend:
    def _open_the_account_center_without_the_backend(self) -> dict:
        # sys.executable and a module-level string constant, no untrusted input.
        return run_probe(
            _ACCOUNT_CENTER_WITHOUT_THE_BACKEND_PROBE,
            "tests.settings_without_backend",
        )

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
        }

    def test_account_center_shows_no_card_from_the_absent_backend(self) -> None:
        # US-3's carried-forward item: the check above predates the card
        # template (mvp_payments/templates/mvp_payments/card.html), so it
        # could only ever assert against navigation markup. Now that the
        # template exists, re-prove the absence against its own markup — the
        # link a card would carry into the backend's first page.
        result = self._open_the_account_center_without_the_backend()

        assert 'href="/account/billing/subscription/"' not in result["content"]


class TestTemplateComments:
    def test_no_template_opens_a_comment_it_does_not_close_on_the_same_line(
        self,
    ) -> None:
        package = Path(mvp_payments.__file__).parent
        offenders = sorted(
            f"{path.relative_to(package)}:{number}"
            for path in package.rglob("*.html")
            for number, line in enumerate(path.read_text().splitlines(), start=1)
            if line.count("{#") != line.count("#}")
        )
        assert offenders == []
