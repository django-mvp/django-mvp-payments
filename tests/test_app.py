"""The package installs and exposes what a consuming project needs from it."""

from pathlib import Path

from django.apps import apps

import mvp_payments


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
