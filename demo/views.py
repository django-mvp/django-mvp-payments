from django.views.generic import TemplateView


class LandingView(TemplateView):
    """The page the components are built for, as far as it exists yet."""

    template_name = "demo/landing.html"
