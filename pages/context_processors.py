from .models import SiteConfiguration

def global_site_config(request):
    try:
        config = SiteConfiguration.objects.first()
        return {'site_config': config}
    except SiteConfiguration.DoesNotExist:
        return {'site_config': None}
