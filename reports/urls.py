from django.urls import path
from .views import ReportListAPIView, ReportDetailAPIView, CategoryListAPIView

urlpatterns = [
    path('categories/', CategoryListAPIView.as_view(), name='api-category-list'),
    path('reports/', ReportListAPIView.as_view(), name='api-report-list'),
    path('reports/<slug:slug>/', ReportDetailAPIView.as_view(), name='api-report-detail'),
]
