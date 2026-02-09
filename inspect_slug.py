import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Report

try:
    r = Report.objects.get(slug='prostacyclin-drug-market')
    print(f"ID: {r.id}")
    print(f"Title: '{r.title}'")
    print(f"Category: '{r.category.name}'")
except Report.DoesNotExist:
    print("Report not found!")
