from .models import SiteConfiguration

def global_site_config(request):
    try:
        config = SiteConfiguration.objects.first()
        # SEO: Generate Canonical URL (force marketsnxt.com and non-www as per guide)
        # Note: request.build_absolute_uri(request.path) is better for dynamic pages, 
        # but the guide wants a fixed preferred domain.
        canonical_url = request.build_absolute_uri(request.path)
        # If the host is not the preferred one, we could replace it here, 
        # but usually django's building logic is enough if production is configured correctly.
        # To be safe and exact:
        if 'marketsnxt.com' in canonical_url and 'www.' in canonical_url:
            canonical_url = canonical_url.replace('www.', '')
        
        return {
            'site_config': config,
            'canonical_url': canonical_url
        }
    except SiteConfiguration.DoesNotExist:
        return {'site_config': None}
