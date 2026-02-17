from rest_framework import serializers
from .models import Lead
from django_recaptcha.fields import ReCaptchaField

class LeadSerializer(serializers.ModelSerializer):
    captcha = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Lead
        fields = '__all__'
