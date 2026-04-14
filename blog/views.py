from django.shortcuts import render
from django.views.generic import ListView, DetailView
from .models import BlogPost

class BlogPostListView(ListView):
    model = BlogPost
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_posts = BlogPost.objects.filter(is_published=True).order_by('-publish_date')
        
        # Section 1: Latest 5
        context['latest_posts'] = all_posts[:5]
        
        # Section 2: Previous up to 10 (Only those older than the latest)
        context['previous_posts'] = all_posts[5:15]
        
        # SEO: Canonical URL
        context['canonical_url'] = self.request.build_absolute_uri(self.request.path)
        return context

    def get_queryset(self):
        # Limit total to 15 (5 latest + 10 previous) to match user preference
        return BlogPost.objects.filter(is_published=True).order_by('-publish_date')[:15]

class BlogPostDetailView(DetailView):
    model = BlogPost
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # SEO: Canonical URL
        context['canonical_url'] = self.request.build_absolute_uri(self.object.get_absolute_url())
        return context
