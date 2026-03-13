from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone

class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Blog Categories"

class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    content = models.TextField(help_text="HTML Content")
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    author = models.CharField(max_length=100, default="Admin")
    
    # SEO
    meta_title = models.CharField(max_length=500, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.TextField(blank=True, null=True)

    is_published = models.BooleanField(default=True)
    publish_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def read_time(self):
        import math
        # Strip HTML tags
        from django.utils.html import strip_tags
        word_count = len(strip_tags(self.content).split())
        read_time_minutes = math.ceil(word_count / 200) # Assuming 200 words per minute
        return read_time_minutes

    @property
    def summary(self):
        from django.utils.html import strip_tags
        return strip_tags(self.content)[:180] + "..."

    def __str__(self):
        return self.title
