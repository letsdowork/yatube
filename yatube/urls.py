from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.contrib.flatpages import views
from django.conf.urls import handler404, handler500
from django.conf.urls.static import static

urlpatterns = [
    path(
        'about-author/',
        views.flatpage,
        {'url': '/about-author/'},
        name='about'
    ),
    path(
        'about-spec/', views.flatpage, {'url': '/about-spec/'}, name='spec'
    ),
    path('about/', include('django.contrib.flatpages.urls')),
    path("auth/", include("users.urls")),
    path("auth/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("", include("posts.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls))
                  ] + urlpatterns
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )

handler404 = "posts.views.page_not_found"
handler500 = "posts.views.server_error"
