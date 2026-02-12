from django import forms
from .models import Lead
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Invisible

class LeadForm(forms.ModelForm):
    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible)
    
    class Meta:
        model = Lead
        fields = ['first_name', 'last_name', 'email', 'country', 'country_code', 'phone', 'company_name', 'message']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Work Email'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'country_code': forms.HiddenInput(),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Work Phone', 'id': 'id_phone'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message', 'rows': 4}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email or '@' not in email:
            raise forms.ValidationError("Please enter a valid email address.")
        return email

class CheckoutForm(forms.ModelForm):
    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible)

    class Meta:
        model = Lead
        fields = ['first_name', 'last_name', 'email', 'country_code', 'phone', 'company_name', 'designation', 'address', 'city', 'state', 'zip_code', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Work Email'}),
            'country_code': forms.HiddenInput(),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Work Phone', 'id': 'id_phone_checkout'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title / Designation'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State / Province'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip / Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email or '@' not in email:
            raise forms.ValidationError("Please enter a valid email address.")
        if len(email.split('@')[1].split('.')) < 2:
             raise forms.ValidationError("Please enter a valid domain name.")
        return email
