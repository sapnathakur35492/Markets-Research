import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Category

def check_categories():
    print("--- Inspecting Categories ---")
    cats = Category.objects.all()
    for cat in cats:
        print(f"ID: {cat.id} | Name: '{cat.name}'")

if __name__ == "__main__":
    check_categories()
