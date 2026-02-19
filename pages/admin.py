from django.contrib import admin
from .models import Page, SiteConfiguration

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'google_analytics_measurement_id', 'google_search_console_verification_code')
    
    def has_add_permission(self, request):
        # Allow adding if no configuration exists, otherwise prevent
        if self.model.objects.exists():
            return False
        return True
