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
from mvp.menus import AccountCenterMenu, MenuGroup, MenuItem

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
    view: type[PaymentPageView] = PaymentPageView

    #: Whether this page gets an entry in the Account Center's navigation.
    #: A page set ``False`` is still routed and still reverses; it is reached
    #: from somewhere else, the way the plans page is reached from a control
    #: on the subscription page. Reachable and navigable are different
    #: questions, and only the second is a menu's business.
    in_navigation: bool = True


@dataclass(frozen=True)
class Contribution:
    """Everything one namespace puts into the Account Center."""

    backend_app_name: str
    namespace: str
    pages: tuple[Page, ...]
    card_template: str
    group_label: str | Promise

    def is_available(self) -> bool:
        """Whether this namespace's backend is installed.

        ``backend_app_name`` is the application's full dotted name, which is
        what the registry matches — not its short label. The two are the same
        string for an application installed at the top level, which is exactly
        why naming it a label would go unnoticed until a backend shipped as a
        sub-package (D16).

        Asks the application registry only: ``ready()`` and the URL
        configuration both call this, and neither may reverse a URL (D3).
        """
        return apps.is_installed(self.backend_app_name)

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
                reverse(self.view_name(page))
        except NoReverseMatch:
            return False
        return True

    def url_patterns(self) -> list[URLPattern]:
        """One route per declared page, addressed by its slug alone.

        The address a reader sees carries no backend name. Which library a
        project chose to talk to its payment provider is not something the
        person reading their subscription has any use for, and the same rule
        already applies to the label heading these pages in the navigation.
        Collision safety lives in the URL *name*, which does carry the
        namespace (ADR 0002), so two backends cannot claim one name however
        their pages are addressed. Two backends installed at once is not a
        supported configuration for other reasons; see the README.

        Every page is routed, including one kept out of the navigation. The
        view is handed this contribution as well as its own page, which is
        how a page addresses a sibling without a second copy of the URL-name
        format living in a template.
        """
        return [
            path(
                f"{page.slug}/",
                page.view.as_view(page=page, contribution=self),
                name=self.url_name(page),
            )
            for page in self.pages
        ]

    def page_url(self, slug: str) -> str:
        """The address of one of this contribution's own pages, by slug."""
        for page in self.pages:
            if page.slug == slug:
                return reverse(self.view_name(page))
        raise LookupError(f"{self.namespace} declares no page with slug {slug!r}")

    def register(self) -> None:
        """Add this namespace's group, holding one entry per navigated page.

        One labelled group rather than a run of entries at the top level: the
        Account Center is shared with whatever else a project installed, and
        django-accounts-center already sections its own part of this menu the
        same way (D19).

        A group whose pages cannot be reached disappears with them, because
        django-flex-menus hides a container left with no visible children.

        Idempotent by group name: ``ready()`` runs again on every
        development-server reload, and the menu tree survives it (D5).
        """
        if AccountCenterMenu.get(self.namespace, maxlevel=1) is not None:
            return
        AccountCenterMenu.append(
            MenuGroup(
                name=self.namespace,
                extra_context={"label": self.group_label},
                children=[
                    MenuItem(
                        name=self.url_name(page),
                        view_name=self.view_name(page),
                        extra_context={"label": page.label, "icon": page.icon},
                    )
                    for page in self.pages
                    if page.in_navigation
                ],
            )
        )

    def url_name(self, page: Page) -> str:
        """This page's URL name, carrying the namespace so two cannot collide (D2)."""
        return f"{self.namespace}-{page.slug}"

    def view_name(self, page: Page) -> str:
        """This page's URL name qualified by the application namespace."""
        return f"{APP_NAMESPACE}:{self.url_name(page)}"
