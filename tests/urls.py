from django.urls import include, path

# The demo project's routes, behind a urlconf of the suite's own so a route
# that exists only to exercise a component has somewhere to go.
urlpatterns = [
    path("", include("demo.urls")),
]
