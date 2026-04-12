from django.db.models import Q
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Report, Category
from .serializers import ReportListSerializer, ReportDetailSerializer, CategorySerializer
from rest_framework.pagination import PageNumberPagination
from django.views.generic import TemplateView, DetailView, ListView
from django.db.models import Count
from django.conf import settings

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        from blog.models import BlogPost
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(report_count=Count('reports')).filter(report_count__gt=0)
        # Only show Global reports on home page
        context['latest_reports'] = Report.objects.filter(region__icontains='Global').select_related('category').order_by('-publish_date')[:12]
        # Get latest 3 published blog posts
        context['latest_blog_posts'] = BlogPost.objects.filter(is_published=True).order_by('-publish_date')[:3]
        return context

class ReportListView(ListView):
    model = Report
    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 10

    def get_queryset(self):
        # Category from URL slug (new SEO format)
        cat_slug = self.kwargs.get('category_slug') or self.request.GET.get('category')
        
        if cat_slug:
            # If we are filtering by category, show ALL reports for that category (Global + Countries)
            queryset = Report.objects.filter(category__slug=cat_slug).select_related('category').all()
        else:
            # Default to Global reports for the main listing if no category is selected
            queryset = Report.objects.filter(region__icontains='Global').select_related('category').all()
            
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(summary__icontains=q))
            
        return queryset.order_by('-publish_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(report_count=Count('reports')).filter(report_count__gt=0)
        context['current_category'] = self.kwargs.get('category_slug') or self.request.GET.get('category', '')
        context['category_slug'] = self.kwargs.get('category_slug', '')
        context['search_query'] = self.request.GET.get('q', '')
        
        # If we have a category slug, get the category object for breadcrumbs/metadata
        if self.kwargs.get('category_slug'):
            context['category_obj'] = Category.objects.filter(slug=self.kwargs.get('category_slug')).first()
            if context['category_obj']:
                context['page_title'] = context['category_obj'].name
        
        # URL name for pagination
        if self.kwargs.get('category_slug'):
            context['page_url_name'] = 'category-report-list-paginated'
        else:
            context['page_url_name'] = 'report-list-paginated'
        
        # Get list of all unique countries available in the database (excluding Global)
        context['available_countries'] = Report.objects.exclude(
            region__icontains='Global'
        ).values_list('region', flat=True).distinct().order_by('region')
        
        if context.get('paginator'):
            context['total_reports_count'] = context['paginator'].count
        else:
            context['total_reports_count'] = self.get_queryset().count()
        
        # Noindex for paginated pages (page 2, 3, etc.)
        page = self.request.GET.get('page') or self.kwargs.get('page')
        if page and str(page) != '1':
            context['noindex'] = True
            
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return context

from django.shortcuts import get_object_or_404, redirect
from django.views import View
from leads.forms import LeadForm

class CategoryOrReportView(View):
    """
    Dispatcher view to handle /reports/<slug>/ pattern.
    Checks if the slug is a Category first, then a Report.
    """
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        
        # Check if it's a category
        if Category.objects.filter(slug=slug).exists():
            # Build clean kwargs — replace 'slug' with 'category_slug'
            clean_kwargs = {k: v for k, v in kwargs.items() if k != 'slug'}
            clean_kwargs['category_slug'] = slug
            return ReportListView.as_view()(request, *args, **clean_kwargs)
        
        # Else treat as a report detail (legacy/direct URL)
        return ReportDetailView.as_view()(request, *args, **kwargs)


class CountryCategoryOrReportView(View):
    """
    Dispatcher view to handle /reports/country-reports/<country_slug>/<slug>/ pattern.
    Checks if the slug is a Category first, then a Report.
    """
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        country_slug = kwargs.get('country_slug')
        
        # Check if it's a category
        if Category.objects.filter(slug=slug).exists():
            # Build clean kwargs — replace 'slug' with 'category_slug', keep 'country_slug'
            clean_kwargs = {k: v for k, v in kwargs.items() if k != 'slug'}
            clean_kwargs['category_slug'] = slug
            return CountryReportListView.as_view()(request, *args, **clean_kwargs)
        
        # Else treat as a report detail
        return ReportDetailView.as_view()(request, *args, **kwargs)


class GlobalReportListView(ReportListView):
    """
    SEO-friendly listing for Global reports.
    URL: /reports/global/ or /reports/global/<category_slug>/
    """
    def get_queryset(self):
        queryset = Report.objects.filter(region__icontains='Global').select_related('category').all()
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(summary__icontains=q))
        return queryset.order_by('-publish_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Global Market Research Reports'
        context['is_global_reports'] = True
        context['selected_category_slug'] = self.kwargs.get('category_slug', '')
        context['category_slug'] = self.kwargs.get('category_slug', '')
        
        if self.kwargs.get('category_slug'):
            context['page_url_name'] = 'global-report-list-category-paginated'
        else:
            context['page_url_name'] = 'global-report-list-paginated'
        return context

class ReportDetailView(DetailView):
    model = Report
    template_name = "reports/report_detail.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lead_form'] = LeadForm()
        # Add related reports from the same category, excluding current report
        context['related_reports'] = Report.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id).order_by('-publish_date')[:6]
        
        # Add categories for sidebar navigation
        context['all_categories'] = Category.objects.annotate(
            report_count=Count('reports')
        ).filter(report_count__gt=0).order_by('name')

        # Pass URL context for breadcrumbs
        from django.utils.text import slugify
        context['category_slug'] = self.kwargs.get('category_slug', self.object.category.slug)
        context['country_slug'] = self.kwargs.get('country_slug', slugify(self.object.region or ''))
        
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return context

class CountryReportListView(ReportListView):
    """
    View to display only Country-specific reports.
    Supports:
      /reports/country-reports/                          -> all country reports
      /reports/country-reports/<country>/                -> filter by country
      /reports/country-reports/<country>/<category>/    -> filter by country + category
    Also supports legacy ?country= query param.
    """
    def get_queryset(self):
        queryset = Report.objects.exclude(region__icontains='Global').select_related('category').all()

        # Country from URL path (e.g. /reports/country-reports/brazil/)
        country_slug = self.kwargs.get('country_slug')
        matched_region = None
        
        if country_slug:
            # Find the actual region name that matches this slug (robust way to handle 'U.S.' -> 'us')
            from django.utils.text import slugify
            all_regions = Report.objects.exclude(region__icontains='Global').values_list('region', flat=True).distinct()
            matched_region = next((r for r in all_regions if slugify(r) == country_slug), None)
            
            if matched_region:
                queryset = queryset.filter(region=matched_region)
            else:
                # Fallback to existing logic
                queryset = queryset.filter(region__iexact=country_slug.replace('-', ' '))

        # Category from URL path (e.g. /reports/country-reports/brazil/healthcare/)
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Also support legacy ?country= query param
        selected_country_param = self.request.GET.get('country')
        if selected_country_param and not country_slug:
            # Try robust match for query param too
            from django.utils.text import slugify
            all_regions = Report.objects.exclude(region__icontains='Global').values_list('region', flat=True).distinct()
            param_matched_region = next((r for r in all_regions if r == selected_country_param or slugify(r) == selected_country_param), None)
            
            if param_matched_region:
                queryset = queryset.filter(region=param_matched_region)
                matched_region = param_matched_region
            else:
                queryset = queryset.filter(region=selected_country_param)
                matched_region = selected_country_param

        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(summary__icontains=q))

        # Category from query param (legacy)
        cat_slug = self.request.GET.get('category')
        if cat_slug and not category_slug:
            queryset = queryset.filter(category__slug=cat_slug)

        self.resolved_region = matched_region # Store for context
        return queryset.order_by('-publish_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Country Reports"
        context['is_country_reports'] = True
        context['country_slug'] = self.kwargs.get('country_slug', '')
        context['category_slug'] = self.kwargs.get('category_slug', '')
        
        # Use the resolved region name if we found one
        resolved_region = getattr(self, 'resolved_region', None)
        context['selected_country'] = resolved_region or self.request.GET.get('country', self.kwargs.get('country_slug', ''))
        
        if self.kwargs.get('country_slug') and self.kwargs.get('category_slug'):
            context['page_url_name'] = 'country-report-list-category-paginated'
        elif self.kwargs.get('country_slug'):
            context['page_url_name'] = 'country-report-list-paginated'
        else:
            context['page_url_name'] = 'country-reports-paginated'
        return context

class ReportMethodologyView(DetailView):
    model = Report
    template_name = "reports/methodology.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lead_form'] = LeadForm()
        # Add related reports from the same category, excluding current report
        context['related_reports'] = Report.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id).order_by('-publish_date')[:6]
        
        # Add categories for sidebar navigation
        context['all_categories'] = Category.objects.annotate(
            report_count=Count('reports')
        ).filter(report_count__gt=0).order_by('name')
        
        return context

class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ReportListAPIView(generics.ListAPIView):
    queryset = Report.objects.select_related('category').all().order_by('-publish_date')
    serializer_class = ReportListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'region', 'format_type']
    search_fields = ['title', 'summary', 'slug']
    ordering_fields = ['publish_date', 'single_user_price']

class ReportDetailAPIView(generics.RetrieveAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportDetailSerializer
    lookup_field = 'slug'

from rest_framework.views import APIView
from rest_framework.response import Response
from django.urls import reverse

class ReportSearchSuggestionsView(APIView):
    """
    API endpoint for search autocomplete/suggestions.
    Returns matching report titles and their detail URLs.
    """
    def get(self, request):
        q = request.GET.get('q', '')
        if len(q) < 2:
            return Response([])
        
        # Search in title and summary
        reports = Report.objects.filter(
            Q(title__icontains=q) | Q(summary__icontains=q)
        ).select_related('category').only('title', 'slug', 'category__slug', 'region')[:10]
        
        results = []
        for r in reports:
            results.append({
                'title': r.title,
                'url': r.get_absolute_url()
            })
        return Response(results)
