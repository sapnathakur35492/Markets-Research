import os
import sys
import django
from django.utils import timezone
import random

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_research_backend.settings')
django.setup()

from reports.models import Category, Report
from django.utils.text import slugify

def create_data():
    categories = [
        "Healthcare", "Technology", "Energy & Power", 
        "Automotive", "Chemicals", "Consumer Goods", 
        "Food & Beverage", "Aerospace"
    ]
    
    cat_objs = []
    for cat in categories:
        c, _ = Category.objects.get_or_create(name=cat, slug=slugify(cat))
        cat_objs.append(c)
        print(f"Category: {cat}")

    titles = [
        "Global Artificial Intelligence Market Size, Share & Trends Analysis",
        "Regenerative Medicine Market Outlook 2024-2030",
        "Electric Vehicle Battery Market - Global Industry Analysis",
        "Sustainable Packaging Market Growth & Forecast",
        "Cybersecurity Insurance Market Trends and Opportunities",
        "Plant-Based Food Market: Global Strategic Business Report",
        "Industrial Automation Market: Industry Trends & Analysis",
        "Telemedicine Market: Global Opportunity Analysis"
    ]

    for i, title in enumerate(titles):
        cat = random.choice(cat_objs)
        price = random.choice([2500, 3500, 4200, 1950, 5000])
        
        Report.objects.get_or_create(
            title=title,
            defaults={
                'slug': slugify(title),
                'category': cat,
                'summary': f"<p>The <strong>{title}</strong> report provides a comprehensive analysis of the market dynamics, including key drivers, restraints, and opportunities. The global market is expected to witness significant growth during the forecast period.</p><p>Key players are focusing on strategic partnerships and product innovations to gain a competitive edge.</p>",
                'toc': "1. Executive Summary\n2. Market Overview\n3. Market Segmentation\n4. Competitive Landscape\n5. Strategic Profiling",
                'publish_date': timezone.now().date(),
                'single_user_price': price,
                'multi_user_price': price * 1.5,
                'enterprise_price': price * 2.5,
                'pages_count': random.randint(120, 350),
                'format_type': "PDF, Excel",
                'region': "Global"
            }
        )
        print(f"Report Created: {title}")

if __name__ == "__main__":
    create_data()
