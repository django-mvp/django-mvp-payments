from mvp.views import MVPTemplateView


class HomeView(MVPTemplateView):
    """What this package is, and where the component pages will appear."""

    template_name = "demo/home.html"
    page_title = "Home"
    page_subtitle = "Payment and subscription interfaces as Cotton components"
    breadcrumbs = [{"text": "Home"}]
