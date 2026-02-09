from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from reports.models import Report, Category
from blog.models import BlogPost
from pages.models import Page

class ReportSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Report.objects.all()
        
    def location(self, obj):
        return f'/reports/{obj.slug}/'

class CategorySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return f'/category/{obj.slug}/'

class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return BlogPost.objects.filter(is_published=True)

    def location(self, obj):
        return f'/blog/{obj.slug}/'

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return Page.objects.all()

    def location(self, obj):
        return f'/{obj.slug}/'
