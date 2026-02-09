import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Report, Category

def forensic_search():
    print("--- Searching for specific strings ---")
    
    # Check Categories again
    bad_cats = Category.objects.filter(name__contains="{{")
    print(f"Categories with '{{': {bad_cats.count()}")
    for c in bad_cats:
        print(f"Bad Category: {c.id} - {c.name}")

    # Check Reports
    bad_reports = Report.objects.filter(summary__contains="Report Snapshot")
    print(f"Reports with 'Report Snapshot': {bad_reports.count()}")
    
    for r in bad_reports:
        print(f"\nReport ID: {r.id}")
        print(f"Title: {r.title}")
        print(f"Category: {r.category.name}")
        print(f"Summary Start: {r.summary[:100]}")
        
    # Check for literal "{{ report.title }}" in Title
    bad_titles = Report.objects.filter(title__contains="{{")
    print(f"\nReports with '{{' in Title: {bad_titles.count()}")
    for r in bad_titles:
        print(f"Bad Title ID: {r.id} - {r.title}")

if __name__ == "__main__":
    forensic_search()
