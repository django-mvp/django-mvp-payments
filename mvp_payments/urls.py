"""The URL configuration a project includes once (FR-001).

Mounts one route per page of every available contribution, under a single
application namespace, so a project gets every installed backend's pages
from one include line::

    urlpatterns = [
        path("payments/", include("mvp_payments.urls")),
    ]
"""

from mvp_payments.namespaces import available_contributions

app_name = "payments"

urlpatterns = [
    pattern
    for contribution in available_contributions()
    for pattern in contribution.url_patterns()
]
