from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from .sitemaps import ReportSitemap, CategorySitemap, BlogSitemap, StaticViewSitemap
from django.views.generic import RedirectView, TemplateView
from reports.views import HomeView

sitemaps = {
    'reports': ReportSitemap,
    'categories': CategorySitemap,
    'blog': BlogSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', HomeView.as_view(), name='home'), # Homepage
    path('admin/', admin.site.urls),
    path('reports/', include('reports.frontend_urls')), # Frontend Reports
    path('api/', include('reports.urls')),
    path('api/leads/', include('leads.urls')),
    path('blog/', include('blog.urls')),
    path('', include('pages.urls')),  # Static pages
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
