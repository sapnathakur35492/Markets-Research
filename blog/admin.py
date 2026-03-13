import json
import datetime
import pandas as pd
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django import forms
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django_ckeditor_5.widgets import CKEditor5Widget
from django.db import models
from reports.utils import auto_format_content
from .models import BlogPost, BlogCategory
import traceback

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditor5Widget(config_name='extends')},
    }
    list_display = ('title', 'category', 'author', 'publish_date', 'is_published')
    list_filter = ('category', 'is_published', 'publish_date')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    change_list_template = "admin/blog_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel, name='blog_import_excel'),
        ]
        return my_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            form = ExcelImportForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = request.FILES["excel_file"]
                try:
                    df = pd.read_excel(excel_file)
                    df.columns = df.columns.str.strip().str.lower()
                    
                    imported_count = 0
                    skipped_count = 0
                    duplicate_titles = []
                    
                    for index, row in df.iterrows():
                        title = str(row.get('title', '')).strip()
                        if not title or title == 'nan':
                            skipped_count += 1
                            continue
                        
                        if BlogPost.objects.filter(title=title).exists():
                            duplicate_titles.append(title)
                            skipped_count += 1
                            continue
                            
                        category_name = str(row.get('category', 'Uncategorized')).strip()
                        category, _ = BlogCategory.objects.get_or_create(name=category_name)
                        
                        # Date handling
                        publish_raw = row.get('publish date') or row.get('publish_date')
                        if pd.isna(publish_raw):
                            publish_date = timezone.now().date()
                        elif isinstance(publish_raw, (datetime.datetime, datetime.date)):
                            publish_date = publish_raw.date() if isinstance(publish_raw, datetime.datetime) else publish_raw
                        else:
                            try:
                                publish_date = pd.to_datetime(publish_raw).date()
                            except:
                                publish_date = timezone.now().date()
                        
                        slug_val = str(row.get('slug', '')).strip()
                        if not slug_val or slug_val == 'nan':
                            slug_val = slugify(title)
                        
                        if BlogPost.objects.filter(slug=slug_val).exists():
                            slug_val = f"{slug_val}-{index}"

                        content_raw = str(row.get('content', '')).strip()
                        content_formatted = auto_format_content(content_raw)

                        BlogPost.objects.create(
                            title=title,
                            slug=slug_val,
                            category=category,
                            content=content_formatted,
                            author=str(row.get('author', 'Admin')).strip(),
                            meta_title=str(row.get('meta title', row.get('meta_title', ''))).strip(),
                            meta_description=str(row.get('meta description', row.get('meta_description', ''))).strip(),
                            meta_keywords=str(row.get('meta keywords', row.get('meta_keywords', ''))).strip(),
                            publish_date=publish_date,
                            is_published=True
                        )
                        imported_count += 1
                    
                    msg = f"Successfully imported {imported_count} new blogs."
                    if duplicate_titles:
                        msg += f" Skipped {len(duplicate_titles)} duplicates."
                    
                    messages.success(request, msg)
                    return redirect("admin:blog_blogpost_changelist")
                    
                except Exception as e:
                    traceback.print_exc()
                    messages.error(request, f"Error processing file: {str(e)}")
                    return redirect("admin:blog_blogpost_changelist")
        else:
            form = ExcelImportForm()
        
        context = {
            "form": form,
            "opts": self.model._meta,
            "title": "Import Blogs from Excel"
        }
        return render(request, "admin/excel_import.html", context)
