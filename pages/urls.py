from django.urls import path
from . import views
from leads.views import ContactFormView

app_name = 'pages'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', ContactFormView.as_view(), name='contact'),
    path('consulting/', views.ConsultingView.as_view(), name='consulting'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('faqs/', views.FAQView.as_view(), name='faqs'),
    path('certifications/', views.CertificationsView.as_view(), name='certifications'),
    path('mission/', views.MissionView.as_view(), name='mission'),
    path('leadership/', views.LeadershipView.as_view(), name='leadership'),
    path('methodology/', views.MethodologyView.as_view(), name='methodology'),
    path('disclaimer/', views.DisclaimerView.as_view(), name='disclaimer'),
    path('governance/', views.GovernanceView.as_view(), name='governance'),
    path('research-disclaimers/', views.ResearchDisclaimersView.as_view(), name='research_disclaimers'),
]
