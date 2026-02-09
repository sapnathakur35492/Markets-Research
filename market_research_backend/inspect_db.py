import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Report, Category

def inspect_db():
    print("--- Inspecting Categories ---")
    for cat in Category.objects.all()[:5]:
        print(f"ID: {cat.id} | Name: '{cat.name}'")

    print("\n--- Inspecting Reports ---")
    for report in Report.objects.all()[:5]:
        print(f"ID: {report.id} | Title: '{report.title}' | Price: {report.single_user_price}")

if __name__ == "__main__":
    inspect_db()
