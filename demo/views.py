"""The demonstration project's own pages."""

from mvp.views import MVPTemplateView


class HomeView(MVPTemplateView):
    """Show what this package is, and where the component pages appear."""

    template_name = "demo/home.html"
    page_title = "Home"
    page_subtitle = "Payment and subscription interfaces as Cotton components"
    breadcrumbs = [{"text": "Home"}]


class PlansUnconfiguredView(MVPTemplateView):
    """Render the package's own Plans template with neither pricing-table value configured.

    Demonstrates the unavailable state (FS-003). The route belongs to the demonstration
    project: nothing under ``mvp_payments/`` knows this view exists.
    """

    template_name = "demo/plans_unconfigured.html"
    page_title = "Plans, unconfigured"
    breadcrumbs = [{"text": "Home", "href": "/"}, {"text": "Plans, unconfigured"}]


class NoLibraryView(MVPTemplateView):
    """Render the pricing table on a page whose provider library never arrived (FS-003)."""

    template_name = "demo/no_library.html"
    page_title = "Library never arrived"
    breadcrumbs = [{"text": "Home", "href": "/"}, {"text": "Library never arrived"}]
