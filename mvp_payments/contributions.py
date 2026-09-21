"""What a namespace declares it contributes to the Account Center.

A namespace speaks to one payment backend and puts three things into the
Account Center when that backend is installed: navigation entries, an
overview card and pages. ``Contribution`` is the one object all three read,
so the three surfaces cannot drift apart from one another (D1). Not a base
class — one instance per namespace, and nothing subclasses it.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps
from django.urls import NoReverseMatch, URLPattern, path, reverse
from django.utils.functional import Promise
from mvp.menus import AccountCenterMenu, MenuItem

from .views import PaymentPageView

#: The application namespace every contributed page's URL name is grouped
#: under (D2). A namespace named after the backend was rejected: a project
#: could then claim it by mounting the backend's own URLs under it.
APP_NAMESPACE = "payments"


@dataclass(frozen=True)
class Page:
    """One page a namespace contributes.

    ``slug`` names the page within its namespace; combined with the
    namespace slug it builds the page's URL name (D2).
    """

    slug: str
    label: str | Promise
    icon: str
    template_name: str


@dataclass(frozen=True)
class Contribution:
    """Everything one namespace puts into the Account Center."""

    backend_app_label: str
    namespace: str
    pages: tuple[Page, ...]
    card_template: str

    def is_available(self) -> bool:
        """Whether this namespace's backend is installed.

        Asks the application registry only: ``ready()`` and the URL
        configuration both call this, and neither may reverse a URL (D3).
        """
        return apps.is_installed(self.backend_app_label)

    def is_reachable(self) -> bool:
        """Whether this namespace's pages actually reverse.

        Only a render-time caller may ask this (D3) — reversing a URL needs
        the URL configuration already loaded, which neither ``ready()`` nor
        the URL configuration itself may assume.
        """
        if not self.is_available():
            return False
        try:
            for page in self.pages:
                reverse(self._view_name(page))
        except NoReverseMatch:
            return False
        return True

    def url_patterns(self) -> list[URLPattern]:
        """One route per declared page, named ``<namespace>-<page slug>``."""
        return [
            path(
                f"{self.namespace}/{page.slug}/",
                PaymentPageView.as_view(page=page),
                name=self._url_name(page),
            )
            for page in self.pages
        ]

    def register(self) -> None:
        """Add one navigation entry per page to the Account Center.

        Idempotent by entry name: ``ready()`` runs again on every
        development-server reload, and the menu tree survives it (D5).
        """
        for page in self.pages:
            entry_name = self._url_name(page)
            if AccountCenterMenu.get(entry_name, maxlevel=1) is not None:
                continue
            AccountCenterMenu.append(
                MenuItem(
                    name=entry_name,
                    view_name=self._view_name(page),
                    extra_context={"label": page.label, "icon": page.icon},
                )
            )

    def _url_name(self, page: Page) -> str:
        return f"{self.namespace}-{page.slug}"

    def _view_name(self, page: Page) -> str:
        return f"{APP_NAMESPACE}:{self._url_name(page)}"
