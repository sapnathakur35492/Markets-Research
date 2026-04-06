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

class PricingView(TemplateView):
    template_name = 'pages/pricing.html'
    
    def get_context_data(self, **kwargs):
        from reports.models import Report
        from django.db.models import Avg
        from django.shortcuts import get_object_or_404
        context = super().get_context_data(**kwargs)
        
        slug = self.request.GET.get('slug')
        pricing_type = self.request.GET.get('type', 'all')
        report = None
        
        if slug:
            report = get_object_or_404(Report, slug=slug)
            context['report'] = report
            # Determine type from report if not explicitly provided or if conflicting
            if 'global' in report.region.lower():
                pricing_type = 'global'
            else:
                pricing_type = 'country'
        
        context['pricing_type'] = pricing_type

        # Get stats
        if report:
            # If report exists, we use its specific prices
            context['global_prices'] = {
                'single': report.single_user_price,
                'multi': report.multi_user_price,
                'enterprise': report.enterprise_price,
                'datapack': report.data_pack_price
            }
            context['country_prices'] = context['global_prices'] # Same for display logic if locked to one
        else:
            # Fallback to averages
            global_stats = Report.objects.filter(region__icontains='Global').aggregate(
                single=Avg('single_user_price'),
                multi=Avg('multi_user_price'),
                enterprise=Avg('enterprise_price'),
                datapack=Avg('data_pack_price')
            )
            
            country_stats = Report.objects.exclude(region__icontains='Global').aggregate(
                single=Avg('single_user_price'),
                multi=Avg('multi_user_price'),
                enterprise=Avg('enterprise_price'),
                datapack=Avg('data_pack_price')
            )
            
            context['global_prices'] = {
                'single': int(global_stats['single'] or 4550),
                'multi': int(global_stats['multi'] or 5450),
                'enterprise': int(global_stats['enterprise'] or 6950),
                'datapack': int(global_stats['datapack'] or 3150)
            }
            
            context['country_prices'] = {
                'single': int(country_stats['single'] or 1850),
                'multi': int(country_stats['multi'] or 2450),
                'enterprise': int(country_stats['enterprise'] or 3150),
                'datapack': int(country_stats['datapack'] or 1050)
            }
        
        # Initial prices based on type
        if pricing_type == 'country':
            context['prices'] = context['country_prices']
        else:
            context['prices'] = context['global_prices']
            
        context['meta_title'] = 'Pricing & Licensing Options - Markets NXT'
        context['meta_description'] = 'Explore flexible licensing options for Markets NXT research reports including Single User, Multi-User, and Enterprise licenses.'
        return context
