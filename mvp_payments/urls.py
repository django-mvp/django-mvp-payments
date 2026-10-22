"""The URL configuration a project includes once.

Mounts one route per page of every available contribution, under a single
application namespace, so a project gets every installed backend's pages
from one include line::

    urlpatterns = [
        path("payments/", include("mvp_payments.urls")),
    ]
"""

from django.apps import apps
from django.urls import URLPattern, URLResolver, include, path

from mvp_payments.contributions import APP_NAMESPACE
from mvp_payments.namespaces import available_contributions

# Contribution.view_name() builds every name against APP_NAMESPACE, so a second
# copy of the string here could silently stop every one of them reversing.
app_name = APP_NAMESPACE

urlpatterns: list[URLPattern | URLResolver] = [
    pattern
    for contribution in available_contributions()
    for pattern in contribution.url_patterns()
]

if apps.is_installed("mvp_payments.stripe"):
    urlpatterns.append(path("", include("mvp_payments.stripe.urls")))
