"""The URL configuration a project includes once (FR-001).

Mounts one route per page of every available contribution, under a single
application namespace, so a project gets every installed backend's pages
from one include line::

    urlpatterns = [
        path("payments/", include("mvp_payments.urls")),
    ]
"""

from mvp_payments.contributions import APP_NAMESPACE
from mvp_payments.namespaces import available_contributions

# One source for the namespace. Contribution.view_name() builds every name
# against APP_NAMESPACE, so a second copy of the string here could silently
# stop every one of them reversing.
app_name = APP_NAMESPACE

urlpatterns = [
    pattern
    for contribution in available_contributions()
    for pattern in contribution.url_patterns()
]
