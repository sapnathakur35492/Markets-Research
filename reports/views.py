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
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(report_count=Count('reports')).filter(report_count__gt=0)
        # Only show Global reports on home page
        context['latest_reports'] = Report.objects.filter(region__icontains='Global').select_related('category').order_by('-publish_date')[:12]
        return context

class ReportListView(ListView):
    model = Report
    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 10

    def get_queryset(self):
        # Default to Global reports unless specified otherwise
        queryset = Report.objects.filter(region__icontains='Global').select_related('category').all()
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(summary__icontains=q))
        
        # Category
        cat_slug = self.request.GET.get('category')
        if cat_slug:
            queryset = queryset.filter(category__slug=cat_slug)
            
        return queryset.order_by('-publish_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(report_count=Count('reports')).filter(report_count__gt=0)
        context['current_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        # Get list of all unique countries available in the database (excluding Global)
        context['available_countries'] = Report.objects.exclude(
            region__icontains='Global'
        ).values_list('region', flat=True).distinct().order_by('region')
        
        # Explicitly pass count to avoid template parsing issues
        if context.get('paginator'):
            context['total_reports_count'] = context['paginator'].count
        else:
            context['total_reports_count'] = self.get_queryset().count()
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return context

from leads.forms import LeadForm

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
        
        context['recaptcha_public_key'] = settings.RECAPTCHA_PUBLIC_KEY
        return context

class CountryReportListView(ReportListView):
    """
    View to display only Country-specific reports.
    Now supports filtering by a specific country via dropdown.
    """
    def get_queryset(self):
        # Exclude "Global" to get all country-specific reports
        queryset = Report.objects.exclude(region__icontains='Global').select_related('category').all()
        
        # Filter by specific country if provided
        selected_country = self.request.GET.get('country')
        if selected_country:
            queryset = queryset.filter(region=selected_country)
            
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(summary__icontains=q))
        
        # Category
        cat_slug = self.request.GET.get('category')
        if cat_slug:
            queryset = queryset.filter(category__slug=cat_slug)
            
        return queryset.order_by('-publish_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Country Reports"
        context['is_country_reports'] = True
        context['selected_country'] = self.request.GET.get('country', '')
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
