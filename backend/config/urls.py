from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from inventory.auth import EmailOrUsernameTokenView

from .desktop_views import desktop_asset, desktop_index

urlpatterns = [
    path("", desktop_index, name="desktop-index"),
    path("desktop/<path:asset_path>", desktop_asset, name="desktop-asset"),
    re_path(
        r"^media/(?P<path>.*)$",
        serve_static,
        {"document_root": settings.MEDIA_ROOT},
        name="local-media",
    ),
    path("admin/", admin.site.urls),
    path("api/auth/login/", EmailOrUsernameTokenView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include("inventory.urls")),
]
