from django.contrib import admin
from django.urls import include, path

# The demo mounts no admin; the admin tests need one.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("demo.urls")),
]
