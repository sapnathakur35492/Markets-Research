from django.urls import path
from .views import LeadCreateAPIView, CapturePaymentView, NewsletterSubscribeAPIView, CreatePayPalOrderView, PayPalReturnView, PayPalCancelView, DevBypassView

urlpatterns = [
    path('inquiry/', LeadCreateAPIView.as_view(), name='lead-create'),
    path('paypal-capture/', CapturePaymentView.as_view(), name='paypal_capture'),
    path('create-paypal-order/', CreatePayPalOrderView.as_view(), name='create-paypal-order'),
    path('paypal-return/', PayPalReturnView.as_view(), name='paypal-return'),
    path('paypal-cancel/', PayPalCancelView.as_view(), name='paypal-cancel'),
    path('dev-bypass/', DevBypassView.as_view(), name='dev-bypass'),
    path('newsletter/', NewsletterSubscribeAPIView.as_view(), name='newsletter-subscribe'),
]
