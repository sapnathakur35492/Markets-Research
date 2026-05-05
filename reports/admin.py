import json
import pandas as pd
import csv
import os
import traceback
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django import forms
from django.conf import settings
from django.utils.text import slugify
from django_ckeditor_5.widgets import CKEditor5Widget
from django.db import models
from .models import Category, Report, ImportBatch
from .utils import auto_format_content, parse_content_sections


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
    formfield_overrides = {
        models.TextField: {'widget': CKEditor5Widget(config_name='extends')},
    }
    list_display = ('title', 'category', 'publish_date', 'region', 'single_user_price')
    list_filter = ('category', 'region', 'format_type')
    search_fields = ('title', 'slug', 'summary')
    readonly_fields = ('sample_url_slug', 'discount_url_slug', 'inquiry_url_slug')
    exclude = (
        'report_highlights', 'industry_snapshot', 'market_growth_catalysts',
        'market_challenges', 'strategic_opportunities', 'market_coverage',
        'geographic_analysis', 'competitive_environment', 'leading_participants',
        'long_term_perspective'
    )
    prepopulated_fields = {'slug': ('title',)}
    change_list_template = "admin/reports_changelist.html"
    actions = ['export_to_excel', 'update_price_action']

    def export_to_excel(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=Reports_Export.csv'
        writer = csv.writer(response)
        headers = ['ID', 'Title', 'Publish Date', 'Region', 'Absolute URL', 'Buy Now', 'Download PDF Sample', 'Ask For Discount', 'Speak to Analyst']
        writer.writerow(headers)

        for obj in queryset:
            report_url = "N/A"
            buy_now_url = "N/A"
            sample_url = "N/A"
            discount_url = "N/A"
            analyst_url = "N/A"
            
            try:
                # Absolute URL
                report_path = reverse('report-detail', kwargs={'slug': obj.slug})
                report_url = request.build_absolute_uri(report_path)
                
                # Buy Now Link (Points to Pricing page as per template)
                region_type = 'global' if obj.region and 'global' in obj.region.lower() else 'country'
                pricing_path = reverse('pages:pricing') + f"?type={region_type}&slug={obj.slug}"
                buy_now_url = request.build_absolute_uri(pricing_path)
                
                # CTA Links
                sample_url = request.build_absolute_uri(reverse('request-sample', kwargs={'slug': obj.slug}))
                discount_url = request.build_absolute_uri(reverse('ask-for-discount', kwargs={'slug': obj.slug}))
                analyst_url = request.build_absolute_uri(reverse('speak-to-analyst', kwargs={'slug': obj.slug}))
            except:
                pass
                
            writer.writerow([
                obj.id, 
                obj.title, 
                obj.publish_date, 
                obj.region, 
                report_url,
                buy_now_url,
                sample_url,
                discount_url,
                analyst_url
            ])
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
                    imported, skipped, duplicates = self.process_excel(excel_file, excel_file.name)
                    
                    if imported > 0:
                        messages.success(request, f"Successfully imported {imported} new reports.")
                    
                    if duplicates:
                        messages.warning(request, f"Skipped {skipped} reports because they already exist.")
                    
                    return redirect("admin:reports_report_changelist")
                    
                except Exception as e:
                    traceback.print_exc()
                    messages.error(request, f"Error: {str(e)}")
                    return redirect("admin:reports_report_changelist")
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
                messages.success(request, f"Updated prices for {count} reports.")
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

    def process_excel(self, file, file_name):
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()
        
        imported_count = 0
        skipped_count = 0
        duplicate_titles = []
        rows_to_import = []
        
        for index, row in df.iterrows():
            report_title = str(row.get('title', '')).strip()
            if not report_title or report_title == 'nan':
                skipped_count += 1
                continue
            if Report.objects.filter(title=report_title).exists():
                duplicate_titles.append(report_title)
                skipped_count += 1
                continue
            rows_to_import.append(row)

        if not rows_to_import:
            return 0, skipped_count, duplicate_titles

        batch = ImportBatch.objects.create(file_name=file_name)

        for row in rows_to_import:
            try:
                category_name = row.get('category')
                category, _ = Category.objects.get_or_create(name=str(category_name).strip())
                
                publish_date = row.get('publish') or row.get('publish_date') or row.get('publish d')
                if pd.isna(publish_date):
                    from django.utils import timezone
                    publish_date = timezone.now().date()
                
                def get_price(val):
                    try:
                        if isinstance(val, str):
                            return float(val.replace(',', '').replace('$', '').strip())
                        return float(val) if pd.notna(val) else 0.0
                    except:
                        return 0.0
                
                raw_content = str(row.get('content', '')).strip()
                formatted_content = auto_format_content(raw_content) if raw_content else ''
                parsed_data = parse_content_sections(formatted_content)
                content_sections = parsed_data.get('sections', {})
                
                report_title = str(row.get('title')).strip()
                Report.objects.create(
                    title=report_title,
                    slug=slugify(row.get('slug')) if row.get('slug') else slugify(report_title),
                    category=category,
                    import_batch=batch,
                    sub_category=str(row.get('sub cate', row.get('sub_category', ''))).strip(),
                    # SEO Fields - Specifically matching headers from user's Excel
                    meta_title=str(row.get('meta title', row.get('meta tit', row.get('meta_title', '')))).strip(),
                    meta_description=str(row.get('meta description', row.get('meta description:', row.get('meta des', row.get('meta_description', ''))))).strip(),
                    meta_keywords=str(row.get('meta keywords', row.get('meta keywords:', row.get('meta key', row.get('meta_keywords', ''))))).strip(),
                    summary=parsed_data.get('cleaned_summary', formatted_content) if parsed_data.get('cleaned_summary') else str(row.get('summary', '')).strip(),
                    toc=parsed_data.get('toc', '') if parsed_data.get('toc') else auto_format_content(str(row.get('toc', '')).strip()),
                    segmentation=parsed_data.get('segmentation', '') if parsed_data.get('segmentation') else auto_format_content(str(row.get('segmentation', '')).strip()),
                    methodology=auto_format_content(str(row.get('methodology', '')).strip()),
                    faqs=parsed_data.get('faqs', '') if parsed_data.get('faqs') else auto_format_content(str(row.get("faq's", row.get('faqs', ''))).strip()),
                    report_highlights=content_sections.get('report_highlights', ''),
                    industry_snapshot=content_sections.get('industry_snapshot', ''),
                    market_growth_catalysts=content_sections.get('market_growth_catalysts', ''),
                    market_challenges=content_sections.get('market_challenges', ''),
                    strategic_opportunities=content_sections.get('strategic_opportunities', ''),
                    market_coverage=content_sections.get('market_coverage', ''),
                    geographic_analysis=content_sections.get('geographic_analysis', ''),
                    competitive_environment=content_sections.get('competitive_environment', ''),
                    leading_participants=content_sections.get('leading_participants', ''),
                    long_term_perspective=content_sections.get('long_term_perspective', ''),
                    pages_count=int(row.get('pages', 0)) if pd.notna(row.get('pages')) else 0,
                    region=str(row.get('region', 'Global')).strip(),
                    format_type=str(row.get('format', row.get('format_type', 'PDF'))).strip(),
                    publish_date=publish_date,
                    base_year=str(row.get('base yea', row.get('base year', ''))).strip(),
                    author=str(row.get('author', '')).strip(),
                    single_user_price=get_price(row.get('single u', row.get('single user license', 0))),
                    multi_user_price=get_price(row.get('multi u', row.get('multi user license', 0))),
                    enterprise_price=get_price(row.get('corporat', row.get('corporate license', 0))),
                    data_pack_price=get_price(row.get('data pac', row.get('data pack excel license', 0))),
                )
                imported_count += 1
            except Exception:
                skipped_count += 1

        batch.report_count = imported_count
        batch.save()
        return imported_count, skipped_count, duplicate_titles

@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'import_date', 'report_count')
    readonly_fields = ('file_name', 'import_date', 'report_count')
    def has_add_permission(self, request): return False
    def delete_model(self, request, obj):
        obj.reports.all().delete()
        super().delete_model(request, obj)
    def delete_queryset(self, request, queryset):
        for obj in queryset: obj.reports.all().delete()
        super().delete_queryset(request, queryset)

admin.site.site_header = "Markets NXT Admin"
admin.site.site_title = "Markets NXT Admin Portal"
