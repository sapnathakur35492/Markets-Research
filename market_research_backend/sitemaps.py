from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from reports.models import Report, Category
from blog.models import BlogPost
from django.utils.text import slugify

class ReportSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Report.objects.all()
        
    def location(self, obj):
        return obj.get_absolute_url()
    
    def lastmod(self, obj):
        return obj.updated_at

class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('category-report-list', kwargs={'category_slug': obj.slug})

class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return BlogPost.objects.filter(is_published=True)

    def location(self, obj):
        return f'/blog/{obj.slug}/'
    
    def lastmod(self, obj):
        return obj.publish_date or obj.created_at

class CountrySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # Get all unique regions except "Global"
        regions = Report.objects.values_list('region', flat=True).distinct()
        return [slugify(r) for r in regions if r and r.lower() != 'global']

    def location(self, obj):
        return reverse('country-report-list', kwargs={'country_slug': obj})

class CountryCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # Get actual region + category pairs that exist in reports
        combos = Report.objects.exclude(region__iexact='Global').values('region', 'category__slug').distinct()
        return combos

    def location(self, obj):
        return reverse('country-report-list-category', kwargs={
            'country_slug': slugify(obj['region']),
            'slug': obj['category__slug']
        })

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        # Direct list of URL names to include based on client's Next.js file
        return [
            'home', 
            'report-list',            # /reports/
            'country-reports',        # /reports/country-reports/
            'blog-list',              # /blog/
            'pages:about', 
            'pages:contact', 
            'pages:consulting',
            'pages:privacy', 
            'pages:terms', 
            'pages:faqs', 
            'pages:pricing',
            'pages:methodology',
        ]

    def location(self, item):
        try:
            return reverse(item)
        except:
            # Fallback if namespaced or named differently
            if item == 'home': return '/'
            if item == 'report-list': return '/reports/'
            if item == 'blog-list': return '/blog/'
            return f'/{item.split(":")[-1]}/'
