from django.shortcuts import render
from django.views.generic import TemplateView

def home(request):
    """Homepage view"""
    return render(request, 'pages/home.html')

# Static Pages Views
class AboutView(TemplateView):
    template_name = 'pages/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'About Us - Markets NXT | A Montclaire & Stein Venture'
        context['meta_description'] = 'Learn about Markets NXT, a legacy rooted in early 20th century enterprise with over a century of institutional research and strategic advisory excellence.'
        return context

class ContactView(TemplateView):
    template_name = 'pages/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Contact Us - Markets NXT'
        context['meta_description'] = 'Get in touch with Markets NXT for market intelligence, strategic advisory, and custom research engagements.'
        return context

class ConsultingView(TemplateView):
    template_name = 'pages/consulting.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Strategic Advisory & Consulting - Markets NXT'
        context['meta_description'] = 'Markets NXT provides consulting-led market intelligence services for strategic decisions, market entry, due diligence, and custom research.'
        return context

class PrivacyView(TemplateView):
    template_name = 'pages/privacy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Privacy Policy - Markets NXT'
        return context

class TermsView(TemplateView):
    template_name = 'pages/terms.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Terms & Conditions - Markets NXT'
        return context

class FAQView(TemplateView):
    template_name = 'pages/faqs.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Frequently Asked Questions - Markets NXT'
        return context

class CertificationsView(TemplateView):
    template_name = 'pages/certifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Certifications & Standards - Markets NXT'
        return context

class MissionView(TemplateView):
    template_name = 'pages/mission.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Mission, Vision & Values - Markets NXT'
        return context

class LeadershipView(TemplateView):
    template_name = 'pages/leadership.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Leadership & Analysts - Markets NXT'
        return context

class MethodologyView(TemplateView):
    template_name = 'pages/methodology.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Research Methodology - Markets NXT'
        return context

class DisclaimerView(TemplateView):
    template_name = 'pages/disclaimer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Legal Disclaimer - Markets NXT'
        return context

class GovernanceView(TemplateView):
    template_name = 'pages/governance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Corporate Governance & Ethics - Markets NXT'
        return context

class ResearchDisclaimersView(TemplateView):
    template_name = 'pages/research_disclaimers.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Research Disclaimers & Citations - Markets NXT'
        return context
