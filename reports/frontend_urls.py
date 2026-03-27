from django.urls import path
from .views import (
    ReportListView, ReportDetailView, ReportMethodologyView,
    CountryReportListView, GlobalReportListView, CategoryOrReportView,
    CountryCategoryOrReportView
)
from leads.views import LeadCaptureView, CheckoutView

urlpatterns = [
    # --- Global Reports ---
    # /reports/                           → all global reports (default)
    path('', ReportListView.as_view(), name='report-list'),
    path('page=<int:page>/', ReportListView.as_view(), name='report-list-paginated'),


    # /reports/global/                    → global report listing
    # /reports/global/<sector>/           → global filtered by sector
    path('global/', GlobalReportListView.as_view(), name='global-report-list'),
    path('global/page=<int:page>/', GlobalReportListView.as_view(), name='global-report-list-paginated'),
    path('global/<slug:category_slug>/', GlobalReportListView.as_view(), name='global-report-list-category'),
    path('global/<slug:category_slug>/page=<int:page>/', GlobalReportListView.as_view(), name='global-report-list-category-paginated'),

    # /reports/global/<sector>/<slug>/    → global report detail
    path('global/<slug:category_slug>/<slug:slug>/', ReportDetailView.as_view(), name='report-detail-global'),
    path('global/<slug:category_slug>/<slug:slug>/methodology/', ReportMethodologyView.as_view(), name='report-methodology-global'),

    # --- Country Reports ---
    # /reports/country-reports/                         → all country reports
    # /reports/country-reports/<country>/               → filter by country (SEO)
    path('country-reports/', CountryReportListView.as_view(), name='country-reports'),
    path('country-reports/page=<int:page>/', CountryReportListView.as_view(), name='country-reports-paginated'),
    path('country-reports/<slug:country_slug>/', CountryReportListView.as_view(), name='country-report-list'),
    path('country-reports/<slug:country_slug>/page=<int:page>/', CountryReportListView.as_view(), name='country-report-list-paginated'),

    # Country report detail OR Category filter dispatcher (excluded category from URL for detail)
    # /reports/country-reports/<country>/<slug>/
    path('country-reports/<slug:country_slug>/<slug:slug>/', CountryCategoryOrReportView.as_view(), name='report-detail-country'),
    path('country-reports/<slug:country_slug>/<slug:slug>/', CountryCategoryOrReportView.as_view(), name='country-report-list-category'),
    path('country-reports/<slug:country_slug>/<slug:category_slug>/page=<int:page>/', CountryReportListView.as_view(), name='country-report-list-category-paginated'),
    path('country-reports/<slug:country_slug>/<slug:slug>/methodology/', ReportMethodologyView.as_view(), name='report-methodology-country'),

    # --- SEO friendly Category and Report detail dispatcher ---
    # This handles both /reports/<category-slug>/ and /reports/<report-slug>/
    path('<slug:slug>/', CategoryOrReportView.as_view(), name='report-detail'),
    path('<slug:category_slug>/page=<int:page>/', ReportListView.as_view(), name='category-report-list-paginated'),
    path('<slug:category_slug>/', ReportListView.as_view(), name='category-report-list'),
    path('<slug:slug>/methodology/', ReportMethodologyView.as_view(), name='report-methodology'),

    # --- Lead Forms ---
    path('request-sample/<slug:slug>/', LeadCaptureView.as_view(), name='request-sample'),
    path('ask-for-discount/<slug:slug>/', LeadCaptureView.as_view(), name='ask-for-discount'),
    path('request-customization/<slug:slug>/', LeadCaptureView.as_view(), name='request-customization'),
    path('speak-to-analyst/<slug:slug>/', LeadCaptureView.as_view(), name='speak-to-analyst'),
]
