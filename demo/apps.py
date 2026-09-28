"""App configuration for the demo project."""

from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate


def name_the_site(sender, **kwargs):
    """Give the example site this project's name.

    The application shell puts the site's name in every page title and in the
    navbar, and ``django.contrib.sites`` seeds a row reading ``example.com``.
    There is no setting for the name, so it is written once the tables exist.

    Args:
        sender: The application whose migrations just ran.
        **kwargs: The rest of the ``post_migrate`` signal's arguments.
    """
    from django.conf import settings
    from django.contrib.sites.models import Site

    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": "localhost:8020", "name": "django-mvp-payments"},
    )


class DemoConfig(AppConfig):
    """Configure the demo application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "demo"
    verbose_name = "Demo"

    def ready(self):
        """Register the sidebar entries and the site-naming hook."""
        from demo import menus  # noqa: F401

        # Django skips post_migrate for an app with no models, so the hook hangs off the
        # sites app, and connecting it before SiteConfig.ready() means example.com is never made.
        post_migrate.connect(name_the_site, sender=apps.get_app_config("sites"))
