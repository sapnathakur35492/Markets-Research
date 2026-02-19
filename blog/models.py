from django.db import models
from django.utils.text import slugify
from django.conf import settings

class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    content = models.TextField(help_text="HTML Content")
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    author = models.CharField(max_length=100, default="Admin")
    
    # SEO
    meta_title = models.CharField(max_length=500, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.TextField(blank=True, null=True)

    is_published = models.BooleanField(default=True)
    publish_date = models.DateField(auto_now_add=True)
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

    def __str__(self):
        return self.title
