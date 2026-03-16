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
from .models import BlogPost, BlogCategory, BlogImportBatch, BlogPostImage

import traceback

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

class BlogPostImageInline(admin.TabularInline):
    model = BlogPostImage
    extra = 1

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditor5Widget(config_name='extends')},
    }
    inlines = [BlogPostImageInline]
    list_display = ('title', 'category', 'author', 'publish_date', 'is_published', 'import_batch')
    list_filter = ('category', 'is_published', 'publish_date', 'import_batch')
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
                    duplicate_count = 0
                    error_count = 0
                    
                    print(f"--- Starting Blog Import: {excel_file.name} ---")
                    
                    # Create batch record
                    batch = BlogImportBatch.objects.create(file_name=excel_file.name)
                    
                    for index, row in df.iterrows():
                        try:
                            title = str(row.get('title', '')).strip()
                            if not title or title.lower() == 'nan':
                                skipped_count += 1
                                continue
                            
                            if BlogPost.objects.filter(title=title).exists():
                                duplicate_count += 1
                                continue
                                
                            category_name = str(row.get('category', 'Uncategorized')).strip()
                            if not category_name or category_name.lower() == 'nan':
                                category_name = 'Uncategorized'
                            category, _ = BlogCategory.objects.get_or_create(name=category_name)
                            
                            # Date handling
                            publish_raw = row.get('publish date') or row.get('publish_date') or row.get('publish')
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
                            if not slug_val or slug_val.lower() == 'nan':
                                slug_val = slugify(title)
                            
                            if BlogPost.objects.filter(slug=slug_val).exists():
                                slug_val = f"{slug_val}-{index}"
    
                            content_raw = str(row.get('content', '')).strip()
                            if not content_raw or content_raw.lower() == 'nan':
                                content_raw = "Content coming soon..."
                                
                            content_formatted = auto_format_content(content_raw)
    
                            BlogPost.objects.create(
                                title=title,
                                slug=slug_val,
                                category=category,
                                import_batch=batch,
                                content=content_formatted,
                                author=str(row.get('author', 'Admin')).strip(),
                                meta_title=str(row.get('meta title', row.get('meta_title', ''))).strip(),
                                meta_description=str(row.get('meta description', row.get('meta_description', ''))).strip(),
                                meta_keywords=str(row.get('meta keywords', row.get('meta_keywords', ''))).strip(),
                                publish_date=publish_date,
                                is_published=True
                            )
                            imported_count += 1
                            print(f"Imported: {title[:30]}...")
                        except Exception as row_error:
                            print(f"Error importing row {index}: {str(row_error)}")
                            error_count += 1
                    
                    # Log final count to batch
                    batch.post_count = imported_count
                    batch.save()
                    
                    msg = f"Import Finished: {imported_count} imported."
                    if duplicate_count:
                        msg += f" {duplicate_count} duplicates skipped."
                    if error_count:
                        msg += f" {error_count} errors occurred."
                    
                    if imported_count > 0:
                        messages.success(request, msg)
                    else:
                        messages.warning(request, msg)
                        
                    return redirect("admin:blog_blogpost_changelist")
                    
                except Exception as e:
                    traceback.print_exc()
                    messages.error(request, f"Critical error processing file: {str(e)}")
                    return redirect("admin:blog_blogpost_changelist")

        else:
            form = ExcelImportForm()
        
        context = {
            "form": form,
            "opts": self.model._meta,
            "title": "Import Blogs from Excel"
        }
        return render(request, "admin/excel_import.html", context)

@admin.register(BlogImportBatch)
class BlogImportBatchAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'import_date', 'post_count')
    readonly_fields = ('file_name', 'import_date', 'post_count')
    
    def has_add_permission(self, request):
        return False

    def delete_model(self, request, obj):
        # Also delete all posts from this batch
        obj.posts.all().delete()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.posts.all().delete()
        super().delete_queryset(request, queryset)
