"""The package installs and exposes what a consuming project needs from it."""

import ast
import importlib.metadata
import re
from pathlib import Path

from django.apps import apps
from packaging.requirements import Requirement

import mvp_payments
from mvp_payments.namespaces.stripe import stripe_contribution
from tests.probes import run_probe

#: The provider app is the one place the interface rules do not reach (Article XI).
_PROVIDER_APP = Path("stripe")


def _interface_files(package: Path, pattern: str = "*"):
    """Yield the package's files outside the provider app."""
    for path in package.rglob(pattern):
        relative = path.relative_to(package)
        if relative.parts[0] != _PROVIDER_APP.name:
            yield path


_SCRIPT_WITH_HOST_SRC = re.compile(
    r"""<script[^>]*\bsrc\s*=\s*['"](?:https?:)?//""", re.IGNORECASE
)

#: Opens the Account Center in a fresh process that never had the backend installed:
#: `urlpatterns` and the navigation entries are both built once, so overriding
#: `INSTALLED_APPS` mid-process would leave them as built with the backend present.
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
for name in ("stripe-subscription", "stripe-plans"):
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

    def test_stripe_namespace_is_where_cotton_looks_for_it(self) -> None:
        namespace = (
            Path(mvp_payments.__file__).parent / "templates" / "cotton" / "stripe"
        )
        assert namespace.is_dir()

    def test_the_app_defines_no_models(self) -> None:
        assert list(apps.get_app_config("mvp_payments").get_models()) == []

    def test_the_interface_owns_no_data(self) -> None:
        package = Path(mvp_payments.__file__).parent
        forbidden = {"models", "forms", "admin", "serializers", "signals", "migrations"}
        found = sorted(
            str(path.relative_to(package))
            for path in _interface_files(package)
            if path.stem in forbidden and (path.suffix == ".py" or path.is_dir())
        )
        assert found == []

    def test_no_interface_module_reaches_a_database_or_a_provider(self) -> None:
        package = Path(mvp_payments.__file__).parent
        banned = ("django.db", "stripe", "paypal", "braintree", "paddle")
        offenders = sorted(
            f"{path.relative_to(package)}: {name}"
            for path in _interface_files(package, "*.py")
            for node in ast.walk(ast.parse(path.read_text()))
            for name in self._imported_names(node)
            if name.startswith(banned)
        )
        assert offenders == []

    @staticmethod
    def _imported_names(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Import):
            return [alias.name for alias in node.names]
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            return [node.module]
        return []

    def test_no_module_outside_the_provider_app_imports_the_sdk(self) -> None:
        package = Path(mvp_payments.__file__).parent
        offenders = sorted(
            str(path.relative_to(package))
            for path in _interface_files(package, "*.py")
            for node in ast.walk(ast.parse(path.read_text()))
            for name in self._imported_names(node)
            if name == "stripe" or name.startswith("stripe.")
        )
        assert offenders == []

    def test_the_base_requirements_are_django_and_django_mvp_only(self) -> None:
        requires = importlib.metadata.requires("django-mvp-payments") or []
        names = {Requirement(r).name.lower() for r in requires if "extra" not in r}
        assert names == {"django", "django-mvp"}

    def test_the_stripe_lite_extra_requires_only_the_sdk(self) -> None:
        requires = importlib.metadata.requires("django-mvp-payments") or []
        extra = [
            Requirement(r)
            for r in requires
            if Requirement(r).marker
            and 'extra == "stripe-lite"' in str(Requirement(r).marker)
        ]
        assert [r.name for r in extra] == ["stripe"]
        assert str(extra[0].specifier) == "<17,>=16"

    def test_the_import_scan_reaches_every_module_this_feature_added(self) -> None:
        package = Path(mvp_payments.__file__).parent
        scanned = {
            path.relative_to(package) for path in _interface_files(package, "*.py")
        }
        added_by_this_feature = {
            Path("apps.py"),
            Path("contributions.py"),
            Path("urls.py"),
            Path("views.py"),
            Path("namespaces/__init__.py"),
            Path("namespaces/stripe.py"),
            Path("namespaces/stripe_plans.py"),
            Path("plans_urls.py"),
            Path("templatetags/__init__.py"),
            Path("templatetags/mvp_payments.py"),
        }
        assert added_by_this_feature <= scanned


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
            "tests.settings_without_stripe_app",
        )

    def test_account_center_shows_nothing_from_the_absent_backend(self) -> None:
        result = self._open_the_account_center_without_the_backend()

        # The page itself still renders, with its own navigation intact — a
        # missing backend is not a broken page.
        assert result["status_code"] == 200
        assert 'aria-label="Account navigation"' in result["content"]

        # No navigation entry and no card: both render the page's label, so
        # one absence check covers both surfaces.
        for page in stripe_contribution.pages:
            assert f"<span>{page.label}</span>" not in result["content"]

        # None of the backend's page addresses resolve.
        assert result["reverses"] == {
            "stripe-subscription": False,
            "stripe-plans": False,
        }

    def test_account_center_shows_no_card_from_the_absent_backend(self) -> None:
        # The absence proved against the card's own markup: the link a card would
        # carry into the backend's first page.
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
