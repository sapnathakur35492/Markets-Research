from django.contrib import admin
from .models import Lead
import csv
from django.http import HttpResponse
from django.urls import reverse

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
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=Leads_Export.csv'
        writer = csv.writer(response)

        # Standardized headers for Excel
        headers = [
            'ID', 'Date', 'Type', 'Report Title', 'Report URL', 
            'Name', 'Email', 'Phone', 'Company', 'Designation', 'Country', 
            'License', 'Message', 'IP'
        ]
        writer.writerow(headers)

        for obj in queryset:
            # Handle Report URL
            report_title = obj.report.title if obj.report else "N/A"
            report_url = "N/A"
            if obj.report:
                try:
                    report_path = reverse('report-detail', kwargs={'slug': obj.report.slug})
                    report_url = request.build_absolute_uri(report_path)
                except:
                    report_url = "URL Error"
            
            # Format Name
            name = obj.full_name or f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.email

            writer.writerow([
                obj.id,
                obj.created_at.strftime('%Y-%m-%d %H:%M'),
                obj.get_lead_type_display(),
                report_title,
                report_url,
                name,
                obj.email,
                f"{obj.country_code or ''} {obj.phone or ''}".strip(),
                obj.company_name,
                obj.designation,
                obj.country,
                obj.get_license_type_display() if obj.license_type else "N/A",
                obj.message,
                obj.ip_address
            ])
            
            # Mark as exported
            obj.is_exported = True
            obj.save()

        return response
    
    export_to_csv.short_description = "Export Selected to CSV"
