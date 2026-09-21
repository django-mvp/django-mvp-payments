"""The demo project, which is where the components get looked at as they land.

It is tested for the same reason ``test_app.py`` tests the template directory:
everything here fails quietly. A Cotton component that cannot be resolved
renders as empty output, a Tailwind class the packaged stylesheet does not emit
does nothing, and a navigation entry whose URL will not resolve is dropped from
the sidebar. None of that raises, so none of it shows up anywhere except in a
browser.
"""

import re


class TestHomePage:
    """The page a reader lands on, and the shell it is drawn inside."""

    def test_page_is_served(self, client, db):
        assert client.get("/").status_code == 200

    def test_page_is_drawn_inside_the_application_shell(self, home_page):
        """The sidebar and the header, not a hand-rolled document.

        The breadcrumb trail is the header's, drawn from what the view
        declares, so its presence says the header is there and reading the page
        rather than merely that some markup rendered.
        """
        assert "<aside" in home_page
        assert 'aria-label="Main navigation"' in home_page
        assert 'aria-label="Breadcrumbs"' in home_page
        assert '<span class="mvp-breadcrumb-text">Home</span>' in home_page

    def test_title_names_the_page_and_the_site(self, home_page):
        """The site half comes from CurrentSiteMiddleware and the named row.

        Without either the title still renders, just with nothing after the
        separator, which is why the whole string is pinned rather than the page
        name alone.
        """
        title = re.search(r"<title>(.*?)</title>", home_page, re.S).group(1)
        assert " ".join(title.split()) == "Home | django-mvp-payments"

    def test_page_heading_is_the_page_title(self, home_page):
        assert re.search(r"<h1[^>]*>\s*Home\s*</h1>", home_page)

    def test_page_says_what_the_package_is(self, home_page):
        """The one thing the page exists to do."""
        assert "&lt;c-drf-stripe.plan-grid&gt;" in home_page
        assert "drf-stripe-subscription" in home_page

    def test_both_ways_of_building_a_page_are_presented_as_equals(self, home_page):
        """G2, and the grid of cards that carries it.

        Cotton renders a component it cannot resolve as empty output, so a
        broken ``c-grid`` or ``c-card`` would take this section off the page
        without raising. Pinning the card markup alongside the sentence is what
        tells a missing component apart from an edit to the prose.
        """
        assert home_page.count("card-title") == 2
        assert "Native" in home_page
        assert "Provider embed" in home_page
        assert "Neither is the fallback for the other." in home_page


class TestSidebarMenu:
    """What the navigation holds while no component exists."""

    def test_the_home_page_is_linked(self, sidebar_navigation):
        assert "<span>Home</span>" in sidebar_navigation
        assert 'href="/"' in sidebar_navigation

    def test_that_is_the_only_entry(self, sidebar_navigation):
        """No component pages exist, so nothing else belongs in the sidebar yet."""
        assert sidebar_navigation.count("<li") == 1

    def test_every_entry_leads_somewhere(self, home_page):
        """A navigation node with no resolving target is a dead control.

        django-mvp draws a node from its leaf template until it has children,
        so a section declared before it holds a page reaches the browser as a
        button carrying the literal text ``href="None"`` — inert, and not
        distinguishable from a working entry by eye.
        """
        assert 'href="None"' not in home_page


class TestThemeSwitching:
    """A component is meant to follow the site's theme rather than fix colours.

    The demo offers several themes so that claim can be looked at, which only
    works if the layout configuration reaches the page. It does so through a
    context processor that is easy to leave out of a settings file, and leaving
    it out costs no error — every configured option simply resolves to nothing.
    """

    def test_every_configured_theme_is_offered_by_the_control(self, home_page):
        for theme in ("light", "dark", "corporate", "dracula"):
            assert f'data-set-theme="{theme}"' in home_page

    def test_the_sidebar_carries_the_configured_title(self, home_page):
        """The other half of the same configuration, read by a different template."""
        assert re.search(
            r'<span class="mvp-sidebar-title[^"]*">django-mvp-payments</span>',
            home_page,
        )
