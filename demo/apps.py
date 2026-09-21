"""App configuration for the demo project."""

from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate


def name_the_site(sender, **kwargs):
    """Give the example site this project's name.

    The application shell puts the site's name in every page title and in the
    navbar, and ``django.contrib.sites`` seeds a row reading ``example.com``.
    There is no setting for the name, so it is written once the tables exist.
    """
    from django.conf import settings
    from django.contrib.sites.models import Site

    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": "localhost:8020", "name": "django-mvp-payments"},
    )


class DemoConfig(AppConfig):
    """Demo app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "demo"
    verbose_name = "Demo"

    def ready(self):
        """Register the sidebar entries and the site-naming hook.

        Importing ``demo.menus`` is what puts the entries into the shell's
        navigation tree, and it has to happen here rather than at module import
        because the items name views.

        The naming hook is hung off the sites app rather than this one. Django
        skips post_migrate for an app with no models module, and this app has
        none, so a hook registered against it would never fire. Running under
        the sites app also guarantees the table exists by then, and registering
        it here — before ``SiteConfig.ready()`` — means this runs first and the
        packaged ``example.com`` row is never created.
        """
        from demo import menus  # noqa: F401

        post_migrate.connect(name_the_site, sender=apps.get_app_config("sites"))
