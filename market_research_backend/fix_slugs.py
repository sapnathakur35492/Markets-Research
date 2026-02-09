import os
import sys
import django
from django.utils.text import slugify

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Report

def fix_slugs():
    print("--- Fixing Slugs ---")
    reports = Report.objects.all()
    fixed_count = 0
    for report in reports:
        original_slug = report.slug
        # If slug has spaces or is empty, fix it
        if not original_slug or ' ' in original_slug:
            new_slug = slugify(original_slug) if original_slug else slugify(report.title)
            
            # Ensure uniqueness if needed (simple version for now)
            if new_slug != original_slug:
                print(f"Fixing ID {report.id}: '{original_slug}' -> '{new_slug}'")
                report.slug = new_slug
                report.save()
                fixed_count += 1
    
    print(f"Fixed {fixed_count} reports.")

if __name__ == "__main__":
    fix_slugs()
