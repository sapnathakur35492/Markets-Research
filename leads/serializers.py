from rest_framework import serializers
from .models import Lead
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class LeadSerializer(serializers.ModelSerializer):
    captcha = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Lead
        fields = '__all__'

    def create(self, validated_data):
        # Remove captcha from validated_data before saving to Lead model
        validated_data.pop('captcha', None)
        return super().create(validated_data)

    def validate_captcha(self, value):
        if not value:
            return value # If not passed, we skip (for agora/legacy)
            
        secret_key = settings.RECAPTCHA_PRIVATE_KEY
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': secret_key,
                'response': value
            },
            timeout=10
        )
        result = response.json()
        logger.info(f"ReCaptcha verification result: {result}")
        
        # if not result.get('success'):
        #     logger.error(f"ReCaptcha verification failed: {result}")
        #     raise serializers.ValidationError("ReCaptcha verification failed. Please try again.")
            
        return value
