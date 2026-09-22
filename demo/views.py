from mvp.views import MVPTemplateView


class HomeView(MVPTemplateView):
    """What this package is, and where the component pages will appear."""

    template_name = "demo/home.html"
    page_title = "Home"
    page_subtitle = "Payment and subscription interfaces as Cotton components"
    breadcrumbs = [{"text": "Home"}]


class PlansUnconfiguredView(MVPTemplateView):
    """The package's own Plans template, reached with neither configured value
    in context (US-4 scenarios 1 and 2).

    This route and its template belong to the demonstration project, not the
    package: nothing under ``mvp_payments/`` knows this view exists.
    """

    template_name = "demo/plans_unconfigured.html"
    page_title = "Plans, unconfigured"
    breadcrumbs = [{"text": "Home", "href": "/"}, {"text": "Plans, unconfigured"}]


class NoLibraryView(MVPTemplateView):
    """The pricing table component on a page whose provider library never
    arrived (US-4 scenario 3) — the demonstration project's own route."""

    template_name = "demo/no_library.html"
    page_title = "Library never arrived"
    breadcrumbs = [{"text": "Home", "href": "/"}, {"text": "Library never arrived"}]
