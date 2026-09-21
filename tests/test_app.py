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

    def test_the_package_ships_no_application_code(self) -> None:
        """One `AppConfig` and no more (Article XII).

        Nothing here is mounted, routed to or requested, and no payment logic
        runs in this package. Asserted rather than remembered, because the
        pressure to add "just a small view" arrives one convenience at a time.
        """
        package = Path(mvp_payments.__file__).parent
        forbidden = {
            "models",
            "views",
            "urls",
            "forms",
            "admin",
            "serializers",
            "signals",
            "migrations",
        }
        found = sorted(
            str(path.relative_to(package))
            for path in package.rglob("*")
            if path.stem in forbidden and (path.suffix == ".py" or path.is_dir())
        )
        assert found == []

        modules = sorted(path.stem for path in package.rglob("*.py"))
        assert modules == ["__init__", "apps"]

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
