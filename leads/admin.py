from django.contrib import admin
from .models import Lead
import csv
from django.http import HttpResponse

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'email', 'lead_type', 'created_at', 'is_exported')
    list_filter = ('lead_type', 'is_exported', 'created_at')
    search_fields = ('full_name', 'email', 'company_name')
    actions = ['export_to_csv']

    def get_name(self, obj):
        if obj.lead_type == 'NEWSLETTER':
            return ""
        return obj.full_name or "-"
    get_name.short_description = 'Full Name'

    def get_fields(self, request, obj=None):
        if obj and obj.lead_type == 'NEWSLETTER':
            return ('email', 'lead_type', 'created_at', 'is_exported')
        return super().get_fields(request, obj)
        
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.lead_type == 'NEWSLETTER':
            return ('lead_type', 'created_at')
        return super().get_readonly_fields(request, obj)

    def export_to_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
            # Mark as exported
            obj.is_exported = True
            obj.save()

        return response
    
    export_to_csv.short_description = "Export Selected to CSV"
