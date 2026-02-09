from django.urls import path
from .views import LeadCreateAPIView, CapturePaymentView, NewsletterSubscribeAPIView

urlpatterns = [
    path('inquiry/', LeadCreateAPIView.as_view(), name='lead-create'),
    path('paypal-capture/', CapturePaymentView.as_view(), name='paypal_capture'),
    path('newsletter/', NewsletterSubscribeAPIView.as_view(), name='newsletter-subscribe'),
]
