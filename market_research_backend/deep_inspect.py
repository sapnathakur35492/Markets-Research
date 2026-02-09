import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Report

def deep_inspect():
    print("--- Checking for Corrupted Data ---")
    reports = Report.objects.all()
    for report in reports:
        if "{{" in report.title or "}}" in report.title:
            print(f"CORRUPT DATA FOUND [ID {report.id}]: {report.title}")
        else:
            print(f"Valid Data [ID {report.id}]: {report.title[:20]}...")

    print(f"Total Reports: {reports.count()}")

if __name__ == "__main__":
    deep_inspect()
