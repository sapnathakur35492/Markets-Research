from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Report(models.Model):
    # Metadata
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="reports")
    sub_category = models.CharField(max_length=255, blank=True, null=True)
    
    # Content
    summary = models.TextField(help_text="Report Description/Summary (HTML)")
    toc = models.TextField(verbose_name="Table of Contents", help_text="HTML Content")
    segmentation = models.TextField(help_text="HTML Content")
    methodology = models.TextField(help_text="HTML Content")
    faqs = models.TextField(verbose_name="FAQs", help_text="JSON or HTML formatted FAQs")

    # Report Meta
    publish_date = models.DateField()
    pages_count = models.IntegerField(default=0)
    base_year = models.CharField(max_length=50, blank=True, null=True)
    forecast_period = models.CharField(max_length=100, blank=True, null=True)
    format_type = models.CharField(max_length=100, default="PDF")
    region = models.CharField(max_length=100, default="Global")
    author = models.CharField(max_length=255, blank=True, null=True)

    # Pricing
    single_user_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    multi_user_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enterprise_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_pack_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)

    # SEO
    meta_title = models.CharField(max_length=500, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.TextField(blank=True, null=True)

    # Generated URLs (for SEO friendliness)
    sample_url_slug = models.CharField(max_length=500, blank=True, null=True)
    discount_url_slug = models.CharField(max_length=500, blank=True, null=True)
    inquiry_url_slug = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Enhanced Content Fields (from Excel)
    report_highlights = models.TextField(blank=True, null=True, help_text="Bullet points highlighting key market insights")
    industry_snapshot = models.TextField(blank=True, null=True, help_text="Overview of the industry and market")
    market_growth_catalysts = models.TextField(blank=True, null=True, help_text="Key factors driving market growth")
    market_challenges = models.TextField(blank=True, null=True, help_text="Challenges and constraints in the market")
    strategic_opportunities = models.TextField(blank=True, null=True, help_text="Strategic growth opportunities")
    market_coverage = models.TextField(blank=True, null=True, help_text="Market coverage overview table/content")
    geographic_analysis = models.TextField(blank=True, null=True, help_text="Geographic performance analysis")
    competitive_environment = models.TextField(blank=True, null=True, help_text="Competitive environment analysis")
    leading_participants = models.TextField(blank=True, null=True, help_text="List of leading market participants")
    long_term_perspective = models.TextField(blank=True, null=True, help_text="Long-term market perspective")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Auto-generate CTAs slugs if not provided
        if not self.sample_url_slug:
            self.sample_url_slug = f"download-sample-{self.slug}"
        if not self.discount_url_slug:
            self.discount_url_slug = f"ask-for-discount-{self.slug}"
        if not self.inquiry_url_slug:
            self.inquiry_url_slug = f"speak-to-analyst-{self.slug}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
