from rest_framework import serializers
from .models import Category, Report
from leads.models import Lead

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ReportListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'title', 'slug', 'category', 'publish_date', 'pages_count', 'format_type', 'single_user_price', 'summary']

class ReportDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Report
        fields = '__all__'

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'
