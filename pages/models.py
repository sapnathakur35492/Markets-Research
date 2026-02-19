from django.db import models
from django.utils.text import slugify

class Page(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    content = models.TextField(help_text="HTML Content")
    
    # SEO
    meta_title = models.CharField(max_length=500, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=255, default="My Site")
    google_analytics_measurement_id = models.CharField(max_length=255, blank=True, null=True, help_text="Enter the Measurement ID only (e.g., G-XXXXXXXXXX). If you paste the full script, we will try to extract the ID.")
    google_search_console_verification_code = models.CharField(max_length=255, blank=True, null=True, help_text="Enter the verification code or the full meta tag (e.g., google-site-verification=XXXXXXXXXX).")

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        # Clean Google Analytics ID
        if self.google_analytics_measurement_id:
            # Check if it looks like a script tag or full URL
            if 'googletagmanager.com' in self.google_analytics_measurement_id or '<script>' in self.google_analytics_measurement_id:
                # Try to extract G-XXXXXXXXXX
                match = re.search(r'G-[A-Z0-9]+', self.google_analytics_measurement_id)
                if match:
                    self.google_analytics_measurement_id = match.group(0)
                else:
                    raise ValidationError({'google_analytics_measurement_id': 'Could not extract a valid Measurement ID (starting with G-). Please enter just the ID.'})
        
        # Clean Google Search Console Code
        if self.google_search_console_verification_code:
            # Check if it's a full meta tag
            if '<meta' in self.google_search_console_verification_code:
                match = re.search(r'content="([^"]+)"', self.google_search_console_verification_code)
                if match:
                    self.google_search_console_verification_code = match.group(1)
                else:
                    raise ValidationError({'google_search_console_verification_code': 'Could not extract the content from the meta tag. Please enter just the code.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.site_name


    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"
