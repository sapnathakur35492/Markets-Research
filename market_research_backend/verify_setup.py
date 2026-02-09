import os
import sys
import django
from django.conf import settings

sys.path.append(os.path.join(os.getcwd(), 'market_research_backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Report, Category
from leads.models import Lead
from blog.models import BlogPost
from pages.models import Page
from django.urls import reverse

def verify_system():
    print("--- Verifying Models ---")
    print(f"Report Model: {Report._meta.verbose_name}")
    print(f"Lead Model: {Lead._meta.verbose_name}")
    print(f"BlogPost Model: {BlogPost._meta.verbose_name}")
    print(f"Page Model: {Page._meta.verbose_name}")
    
    print("\n--- Verifying URLs ---")
    try:
        print(f"Reports API: {reverse('report-list')}")
        print(f"Leads API: {reverse('lead-create')}")
        print(f"Sitemap: {reverse('django.contrib.sitemaps.views.sitemap')}")
        print("URL Configuration: OK")
    except Exception as e:
        print(f"URL Configuration Failed: {e}")

    print("\n--- Verifying Admin Registry ---")
    from django.contrib import admin
    registry = [m._meta.model_name for m in admin.site._registry]
    expected = ['report', 'category', 'lead', 'blogpost', 'page']
    missing = [m for m in expected if m not in registry]
    
    if not missing:
        print("All models registered in Admin: OK")
    else:
        print(f"Missing models in Admin: {missing}")

if __name__ == "__main__":
    verify_system()
