import sys
from django.test import Client
from django.test.utils import setup_test_environment
setup_test_environment()
from reports.models import Report, Category
from leads.models import Lead

# Setup data
from django.utils import timezone
try:
    category, _ = Category.objects.get_or_create(name="Automotive")
    report, created = Report.objects.get_or_create(
        title="Test Report",
        defaults={
            'slug': 'test-report',
            'category': category,
            'single_user_price': 100,
            'multi_user_price': 200,
            'enterprise_price': 300,
            'data_pack_price': 50,
            'publish_date': timezone.now().date(),
        }
    )
    if not created:
        report.single_user_price = 100
        report.multi_user_price = 200
        report.enterprise_price = 300
        report.save()
        
    print(f"Report: {report.title} ({report.slug}) Created/Found")
except Exception as e:
    print(f"Error setting up data: {e}")
    sys.exit(1)

client = Client()

# 1. VERIFY GET Checkout Page
print("\n--- Verifying POST Checkout ---")
url = f"/reports/checkout/{report.slug}/enterprise/"
response = client.get(url)

if response.status_code == 200:
    print("GET checkout page: SUCCESS (200 OK)")
    # Check context
    price = response.context['price']
    license_type = response.context['license_type']
    if price == 300 and license_type == 'enterprise':
        print(f"Context Verification: SUCCESS (Price: {price}, License: {license_type})")
    else:
         print(f"Context Verification: FAILED (Price: {price}, License: {license_type})")
else:
    print(f"GET checkout page: FAILED ({response.status_code})")
    sys.exit(1)

# 2. VERIFY POST Checkout Form
print("\n--- Verifying POST Checkout Form ---")
data = {
    'full_name': 'Test User',
    'email': 'testuser@example.com',
    'phone': '1234567890',
    'company_name': 'Test Corp',
    'designation': 'Manager',
    'address': '123 Test St',
    'city': 'Test City',
    'state': 'TS',
    'zip_code': '12345',
    'country': 'Test Country',
}

response = client.post(url, data)
# Expect header redirect to report detail
if response.status_code == 302:
    print("POST checkout form: SUCCESS (Redirects)")
    
    # Verify DB
    last_lead = Lead.objects.last()
    if last_lead.email == 'testuser@example.com' and last_lead.lead_type == 'PURCHASE' and last_lead.address == '123 Test St' and last_lead.license_type == 'enterprise':
        print(f"Database Verification: SUCCESS (Lead Saved: {last_lead})")
        print(f"  - Lead Type: {last_lead.lead_type}")
        print(f"  - License Type: {last_lead.license_type}")
        print(f"  - Address: {last_lead.address}")
    else:
        print("Database Verification: FAILED")
        print(f"  Lead: {last_lead}")
        print(f"  Email: {last_lead.email}")
        print(f"  Type: {last_lead.lead_type}")
else:
     print(f"POST checkout form: FAILED (Status: {response.status_code})")
     if response.context and 'form' in response.context:
         print(f"Form Errors: {response.context['form'].errors}")
