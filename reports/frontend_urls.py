from django.urls import path
from .views import ReportListView, ReportDetailView, ReportMethodologyView
from leads.views import LeadCaptureView, CheckoutView

urlpatterns = [
    path('', ReportListView.as_view(), name='report-list'),
    path('<slug:slug>/', ReportDetailView.as_view(), name='report-detail'),
    path('<slug:slug>/methodology/', ReportMethodologyView.as_view(), name='report-methodology'),
    
    # Lead Forms
    path('request-sample/<slug:slug>/', LeadCaptureView.as_view(), name='request-sample'),
    path('ask-for-discount/<slug:slug>/', LeadCaptureView.as_view(), name='ask-for-discount'),
    path('request-customization/<slug:slug>/', LeadCaptureView.as_view(), name='request-customization'),
    path('speak-to-analyst/<slug:slug>/', LeadCaptureView.as_view(), name='speak-to-analyst'),
    
    # Checkout
    path('checkout/<slug:slug>/<str:license_type>/', CheckoutView.as_view(), name='checkout'),
]
