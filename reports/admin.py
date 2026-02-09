from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
from django.utils.text import slugify
from .models import Category, Report
import pandas as pd
from django import forms
from django.conf import settings
import os
import csv
from django.http import HttpResponse

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

class PriceUpdateForm(forms.Form):
    price_action = forms.ChoiceField(choices=[
        ('increase_percent', 'Increase manually by %'),
        ('decrease_percent', 'Decrease manually by %'),
    ])
    value = forms.DecimalField(help_text="Enter percentage (e.g. 10 for 10%)")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'publish_date', 'region', 'single_user_price')
    list_filter = ('category', 'region', 'format_type')
    search_fields = ('title', 'slug', 'summary')
    # Removed 'slug' from readonly_fields to allow editing
    readonly_fields = ('sample_url_slug', 'discount_url_slug', 'inquiry_url_slug')
    prepopulated_fields = {'slug': ('title',)}
    change_list_template = "admin/reports_changelist.html"
    actions = ['export_to_excel', 'update_price_action']

    def export_to_excel(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response
    
    export_to_excel.short_description = "Export Selected to CSV"

    def update_price_action(self, request, queryset):
        selected = queryset.values_list('pk', flat=True)
        return redirect(f'update-prices/?ids={",".join(map(str, selected))}')
        
    update_price_action.short_description = "Update Prices Globally"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel, name='report_import_excel'),
            path('update-prices/', self.update_prices_view, name='report_update_prices'),
        ]
        return my_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            form = ExcelImportForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = request.FILES["excel_file"]
                try:
                    self.process_excel(excel_file)
                    self.message_user(request, "Reports imported successfully")
                    return redirect("admin:reports_report_changelist")
                except Exception as e:
                    self.message_user(request, f"Error importing file: {e}", level=messages.ERROR)
        else:
            form = ExcelImportForm()
        
        context = {
            "form": form,
            "opts": self.model._meta,
            "title": "Import Reports from Excel"
        }
        return render(request, "admin/excel_import.html", context)

    def update_prices_view(self, request):
        ids = request.GET.get('ids', '').split(',')
        if request.method == "POST":
            form = PriceUpdateForm(request.POST)
            if form.is_valid():
                action = form.cleaned_data['price_action']
                val = form.cleaned_data['value']
                reports = Report.objects.filter(id__in=ids)
                count = 0
                for report in reports:
                    multiplier = 1 + (val / 100) if action == 'increase_percent' else 1 - (val / 100)
                    report.single_user_price *= multiplier
                    report.multi_user_price *= multiplier
                    report.enterprise_price *= multiplier
                    report.save()
                    count += 1
                self.message_user(request, f"Updated prices for {count} reports.")
                return redirect("admin:reports_report_changelist")
        else:
            form = PriceUpdateForm()

        context = {
            "form": form,
            "reports_count": len(ids) if ids[0] else 0,
            "opts": self.model._meta,
            "title": "Global Price Update"
        }
        return render(request, "admin/price_update.html", context)

    def process_excel(self, file):
        from .utils import auto_format_content, parse_content_sections
        
        try:
            df = pd.read_excel(file)
            # Normalize column names by removing whitespace
            df.columns = df.columns.str.strip()
            
            for index, row in df.iterrows():
                try:
                    category_name = row.get('Category') or row.get('category')
                    if not category_name:
                        continue
                    
                    category, _ = Category.objects.get_or_create(name=str(category_name).strip())
                    
                    # Date handling
                    publish_date = row.get('Publish') or row.get('publish_date')
                    if pd.isna(publish_date):
                        from django.utils import timezone
                        publish_date = timezone.now().date()
                    
                    # Helper to get price
                    def get_price(val):
                        try:
                            if isinstance(val, str):
                                return float(val.replace(',', '').replace('$', '').strip())
                            return float(val) if pd.notna(val) else 0.0
                        except:
                            return 0.0
                    
                    # Get content and auto-format it
                    raw_content = str(row.get('content', row.get('Content', ''))).strip()
                    formatted_content = auto_format_content(raw_content) if raw_content else ''
                    
                    # Parse content sections from the formatted content
                    # Returns: {'sections': {...}, 'toc': str, 'segmentation': str, 'faqs': str, 'cleaned_summary': str}
                    parsed_data = parse_content_sections(formatted_content)
                    content_sections = parsed_data.get('sections', {})
                    parsed_toc = parsed_data.get('toc', '')
                    parsed_segmentation = parsed_data.get('segmentation', '')
                    parsed_faqs = parsed_data.get('faqs', '')
                    cleaned_summary = parsed_data.get('cleaned_summary', formatted_content)
                    
                    # Get other content fields and auto-format them too
                    raw_toc = str(row.get('TOC', row.get('toc', ''))).strip()
                    formatted_toc = auto_format_content(raw_toc) if raw_toc else ''
                    
                    raw_methodology = str(row.get('Methodology', row.get('methodology', ''))).strip()
                    formatted_methodology = auto_format_content(raw_methodology) if raw_methodology else ''
                    
                    raw_faqs = str(row.get("FAQ's", row.get('faqs', ''))).strip()
                    formatted_faqs = auto_format_content(raw_faqs) if raw_faqs else ''

                    raw_segmentation = str(row.get('Segment', row.get('segmentation', ''))).strip()
                    formatted_segmentation = auto_format_content(raw_segmentation) if raw_segmentation else ''

                    report, created = Report.objects.update_or_create(
                        title=str(row.get('Title', row.get('title'))).strip(),
                        defaults={
                            'slug': slugify(row.get('Slug', row.get('slug'))) if row.get('Slug') or row.get('slug') else slugify(row.get('Title', row.get('title'))),
                            'category': category,
                            'sub_category': str(row.get('Sub Cate', row.get('sub_category', ''))).strip(),
                            'meta_title': str(row.get('Meta Title', row.get('meta_title', ''))).strip(),
                            'meta_description': str(row.get('Meta Des', row.get('meta_description', ''))).strip(),
                            'meta_keywords': str(row.get('Meta Key', row.get('meta_keywords', ''))).strip(),
                            # Use cleaned summary (with TOC and Segmentation removed)
                            'summary': cleaned_summary if cleaned_summary else str(row.get('Summary', row.get('summary', ''))).strip(),
                            # Use parsed TOC if available, otherwise use formatted TOC from Excel column
                            'toc': parsed_toc if parsed_toc else formatted_toc,
                            # Use parsed segmentation if available, otherwise use formatted segmentation from Excel column
                            'segmentation': parsed_segmentation if parsed_segmentation else formatted_segmentation,
                            'methodology': formatted_methodology,  # Auto-formatted methodology
                            # Use parsed FAQs if available, otherwise use formatted FAQs from Excel column
                            'faqs': parsed_faqs if parsed_faqs else formatted_faqs,
                            # New content section fields parsed from Content column
                            'report_highlights': content_sections.get('report_highlights', ''),
                            'industry_snapshot': content_sections.get('industry_snapshot', ''),
                            'market_growth_catalysts': content_sections.get('market_growth_catalysts', ''),
                            'market_challenges': content_sections.get('market_challenges', ''),
                            'strategic_opportunities': content_sections.get('strategic_opportunities', ''),
                            'market_coverage': content_sections.get('market_coverage', ''),
                            'geographic_analysis': content_sections.get('geographic_analysis', ''),
                            'competitive_environment': content_sections.get('competitive_environment', ''),
                            'leading_participants': content_sections.get('leading_participants', ''),
                            'long_term_perspective': content_sections.get('long_term_perspective', ''),
                            'pages_count': int(row.get('Pages', row.get('pages', 0))) if pd.notna(row.get('Pages', row.get('pages'))) else 0,
                            'region': str(row.get('Region', row.get('region', 'Global'))).strip(),
                            'format_type': str(row.get('Format', row.get('format_type', 'PDF'))).strip(),
                            'publish_date': publish_date,
                            'base_year': str(row.get('Base Year', row.get('base_year', ''))).strip(),
                            'author': str(row.get('Author', row.get('author', ''))).strip(),
                            'single_user_price': get_price(row.get('Single User License', row.get('Single User', row.get('single_user_price')))),
                            'multi_user_price': get_price(row.get('Multi User License', row.get('Multi User', row.get('multi_user_price')))),
                            'enterprise_price': get_price(row.get('Corporate License', row.get('Corporate', row.get('enterprise_price')))),
                            'data_pack_price': get_price(row.get('Data Pack Excel License', row.get('Data Pack', row.get('data_pack_price')))),
                        }
                    )
                except Exception as row_error:
                    print(f"Error processing row {index}: {row_error}")
                    continue
        except Exception as e:
            raise Exception(f"Failed to parse Excel file: {str(e)}")

admin.site.site_header = "Market Research Admin"
admin.site.site_title = "Market Research Admin Portal"
