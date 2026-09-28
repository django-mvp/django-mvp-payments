"""What a namespace declares it contributes to the Account Center.

A namespace speaks to one payment backend and puts three things into the
Account Center when that backend is installed: navigation entries, an
overview card and pages. ``Contribution`` is the one object all three read,
so the three surfaces cannot drift apart from one another (ADR 0001). Not a
base class: one instance per namespace, and nothing subclasses it.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps
from django.urls import NoReverseMatch, URLPattern, path, reverse
from django.utils.functional import Promise
from mvp.menus import AccountCenterMenu, MenuGroup, MenuItem

from .views import PaymentPageView

#: The application namespace every contributed page's URL name is grouped
#: under. Not the backend's name, which a project could claim by mounting the
#: backend's own URLs under it (ADR 0002).
APP_NAMESPACE = "payments"


@dataclass(frozen=True)
class Page:
    """One page a namespace contributes.

    Attributes:
        slug: Names the page within its namespace. Combined with the namespace
            it builds the page's URL name (ADR 0002).
        label: The page's title, and its navigation entry's label.
        icon: The django-mvp icon name for the page's entry and card.
        template_name: The template the page renders.
        view: The view class that renders the page (ADR 0006).
        in_navigation: Whether the page gets an entry in the Account Center's
            navigation. A page left out is still routed and still reverses.
    """

    slug: str
    label: str | Promise
    icon: str
    template_name: str
    view: type[PaymentPageView] = PaymentPageView
    in_navigation: bool = True


@dataclass(frozen=True)
class Contribution:
    """Everything one namespace puts into the Account Center.

    Attributes:
        backend_app_name: The backend application's full dotted name.
        namespace: The namespace's slug, which prefixes its URL names.
        pages: The pages the namespace contributes, the first one heading its card.
        card_template: The template of the namespace's overview card.
        group_label: The label of the navigation group holding its entries.
    """

    backend_app_name: str
    namespace: str
    pages: tuple[Page, ...]
    card_template: str
    group_label: str | Promise

    def is_available(self) -> bool:
        """Report whether this namespace's backend is installed.

        Matches the application's full dotted name, not its short label. The
        two only differ for a backend shipped as a sub-package (FS-001).

        Asks the application registry only: ``ready()`` and the URL
        configuration both call this, and neither may reverse a URL.

        Returns:
            Whether the backend application is installed.
        """
        return apps.is_installed(self.backend_app_name)

    def is_reachable(self) -> bool:
        """Report whether this namespace's pages actually reverse.

        Only a render-time caller may ask this: reversing a URL needs the URL
        configuration already loaded, which neither ``ready()`` nor the URL
        configuration itself may assume (FS-001).

        Returns:
            Whether the backend is installed and every page's URL reverses.
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
        """Build one route per declared page, addressed by its slug alone.

        The address a reader sees carries no backend name. Collision safety
        lives in the URL *name*, which does carry the namespace (ADR 0002).

        Every page is routed, including one kept out of the navigation. The
        view is handed this contribution as well as its own page, which is
        how a page addresses a sibling without a second copy of the URL-name
        format living in a template.

        Returns:
            One URL pattern per page.
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
        """Reverse one of this contribution's own pages.

        Args:
            slug: The slug of the page to address.

        Returns:
            The page's URL path.

        Raises:
            LookupError: This contribution declares no page with that slug.
        """
        for page in self.pages:
            if page.slug == slug:
                return reverse(self.view_name(page))
        raise LookupError(f"{self.namespace} declares no page with slug {slug!r}")

    def register(self) -> None:
        """Add this namespace's group, holding one entry per navigated page.

        One labelled group rather than a run of entries at the top level,
        because the Account Center is shared with whatever else a project
        installed (FS-001).

        A group whose pages cannot be reached disappears with them, because
        django-flex-menus hides a container left with no visible children.

        Idempotent by group name: ``ready()`` runs again on every
        development-server reload, and the menu tree survives it.
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
        """Name a page's URL, carrying the namespace so two cannot collide.

        Args:
            page: One of this contribution's pages.

        Returns:
            The URL name, without the application namespace (ADR 0002).
        """
        return f"{self.namespace}-{page.slug}"

    def view_name(self, page: Page) -> str:
        """Name a page's URL, qualified by the application namespace.

        Args:
            page: One of this contribution's pages.

        Returns:
            The name to reverse the page by.
        """
        return f"{APP_NAMESPACE}:{self.url_name(page)}"
