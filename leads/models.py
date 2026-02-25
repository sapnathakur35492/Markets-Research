from django.db import models
from reports.models import Report

class Lead(models.Model):
    LEAD_TYPES = (
        ('CONTACT', 'Contact Us'),
        ('SAMPLE', 'Request Sample'),
        ('DISCOUNT', 'Ask for Discount'),
        ('CUSTOMIZATION', 'Request Customization'),
        ('CALLBACK', 'Get a Call Back'),
        ('PURCHASE', 'Purchase Report'),
        ('NEWSLETTER', 'Newsletter Subscription'),
    )

    LICENSE_TYPES = (
        ('single', 'Single User'),
        ('multi', 'Multi User'),
        ('enterprise', 'Enterprise'),
        ('data', 'Data Pack'),
    )

    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True) # Keeping for legacy
    email = models.EmailField()
    country_code = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # New Address Fields
    address = models.CharField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    
    lead_type = models.CharField(max_length=20, choices=LEAD_TYPES, default='CONTACT')
    license_type = models.CharField(max_length=20, choices=LICENSE_TYPES, blank=True, null=True)
    
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, blank=True, null=True, related_name="leads")
    message = models.TextField(blank=True, null=True)
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_exported = models.BooleanField(default=False)

    def __str__(self):
        name = self.full_name or self.email
        return f"{name} - {self.get_lead_type_display()}"
