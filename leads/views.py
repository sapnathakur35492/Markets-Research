from django.views.generic.edit import CreateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from reports.models import Report
from .models import Lead
from .forms import LeadForm, CheckoutForm
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response
from .serializers import LeadSerializer
import logging
import os
import threading

logger = logging.getLogger(__name__)

def send_lead_emails_task(lead):
    """
    Sends emails in a background task to avoid blocking the response.
    """
    try:
        full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.full_name or "Unknown"
        
        # 1. Email to Admin
        # We put the sender's email in the SUBJECT line so you can see it in the inbox list
        # since Gmail overrides the 'From' address.
        subject_admin = f"New Lead from {lead.email} - {lead.get_lead_type_display()}"
        
        extra_details = ""
        if lead.lead_type == 'PURCHASE':
            extra_details = f"""
            License Type: {lead.get_license_type_display()}
            Address: {lead.address}, {lead.city}, {lead.state}, {lead.zip_code}, {lead.country}
            """
            
        # Refined Email Body: Conditionally include fields
        report_line = f"Report: {lead.report.title}" if lead.report else ""
        designation_line = f"Designation: {lead.designation}" if lead.designation else ""
        company_line = f"Company: {lead.company_name}" if lead.company_name else ""
        
        # Build message using only present fields to keep it clean
        message_lines = [
            f"New Lead Received from {full_name} ({lead.email}):",
            "-" * 30,
            f"Name: {full_name}",
            f"Email: {lead.email}",
            f"Phone: ({lead.country_code or ''}) {lead.phone}",
            f"Type: {lead.get_lead_type_display()}",
            company_line,
            designation_line,
            f"Message: {lead.message}",
            report_line,
            extra_details
        ]
        
        # Join non-empty lines
        message_admin = "\n".join([line for line in message_lines if line.strip()])

        logger.info(f"Sending admin email for lead {lead.id} to {settings.CONTACT_EMAIL}")
        
        # We revert to sending from DEFAULT_FROM_EMAIL to ensure delivery,
        # but we rely on the SUBJECT line and REPLY-TO for identification.
        email = EmailMessage(
            subject_admin,
            message_admin,
            settings.DEFAULT_FROM_EMAIL, # Use authenticated sender to prevent blocking
            [settings.CONTACT_EMAIL], 
            reply_to=[lead.email]        # Reply goes to user
        )
        email.send(fail_silently=False)
        
        logger.info("Admin email sent successfully")

        # 2. Key Acknowledgement to User
        subject_user = "Thank you for contacting Market Research"
        if lead.lead_type == 'PURCHASE':
             subject_user = "Order Confirmation - Market Research"
             message_user = f"Hi {full_name},\n\nThank you for your order of '{lead.report.title}'.\nWe have received your request for the {lead.get_license_type_display()} license.\nOur team will process your order and send you the download link shortly.\n\nBest Regards,\nMarket Research Team"
        else:
            message_user = f"Hi {full_name},\n\nWe have received your inquiry regarding '{lead.get_lead_type_display()}'. Our team will get back to you shortly.\n\nBest Regards,\nMarket Research Team"
            
        logger.info(f"Sending acknowledgment email to user {lead.email}")
        send_mail(
            subject_user,
            message_user,
            settings.DEFAULT_FROM_EMAIL,
            [lead.email],
            fail_silently=False,
        )
        logger.info("User acknowledgment email sent successfully")

    except Exception as e:
        logger.error(f"Error sending lead emails: {e}", exc_info=True)
        # In a thread, we can't show messages to user, so we just log clearly

class LeadCreateAPIView(generics.CreateAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer

    def perform_create(self, serializer):
        lead = serializer.save()
        # Run email in thread
        threading.Thread(target=send_lead_emails_task, args=(lead,)).start()

    # Deprecated/Removed method as it's extracted to global function

class LeadCaptureView(CreateView):
    model = Lead
    form_class = LeadForm
    template_name = 'leads/lead_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(Report, slug=self.kwargs.get('slug'))
        self.lead_type_slug = self.kwargs.get('lead_type') 
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.report
        
        # Determine Title based on URL or Type
        url_name = self.request.resolver_match.url_name
        if 'sample' in url_name:
            context['page_title'] = "Request Sample"
            context['lead_type_code'] = "SAMPLE"
        elif 'discount' in url_name:
            context['page_title'] = "Ask for Discount"
            context['lead_type_code'] = "DISCOUNT"
        elif 'analyst' in url_name:
            context['page_title'] = "Speak to Analyst"
            context['lead_type_code'] = "CALLBACK"
        else:
            context['page_title'] = "Contact Us"
            context['lead_type_code'] = "CONTACT"
            
        return context

    def form_valid(self, form):
        form.instance.report = self.report
        context = self.get_context_data()
        form.instance.lead_type = context['lead_type_code']
        
        # Sync full_name for backward compatibility or display
        first = form.cleaned_data.get('first_name', '')
        last = form.cleaned_data.get('last_name', '')
        form.instance.full_name = f"{first} {last}".strip()
        
        response = super().form_valid(form)
        
        # Async Email Sending
        threading.Thread(target=send_lead_emails_task, args=(self.object,)).start()
        messages.success(self.request, "Your request has been submitted successfully!")
        
        return response

    def get_success_url(self):
        return reverse('report-detail', kwargs={'slug': self.report.slug})

    def form_invalid(self, form):
        # User requested no global error messages/popups, only inline field errors.
        # messages.error(self.request, "Please correct the errors in the form.")
        return super().form_invalid(form)

class CheckoutView(CreateView):
    model = Lead
    form_class = CheckoutForm
    template_name = 'leads/checkout.html'

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(Report, slug=self.kwargs.get('slug'))
        self.license_type = self.kwargs.get('license_type')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.report
        context['license_type'] = self.license_type
        
        # Calculate Price
        price = 0
        license_label = "Unknown License"
        
        if self.license_type == 'single':
            price = self.report.single_user_price
            license_label = "Single User License"
        elif self.license_type == 'multi':
            price = self.report.multi_user_price
            license_label = "Multi User License"
        elif self.license_type == 'enterprise':
            price = self.report.enterprise_price
            license_label = "Enterprise License"
        elif self.license_type == 'data':
            price = self.report.data_pack_price
            license_label = "Data Pack"
            
        context['price'] = price
        context['license_label'] = license_label
        context['PAYPAL_CLIENT_ID'] = os.environ.get('PAYPAL_CLIENT_ID', 'sb')
        return context

    def form_valid(self, form):
        form.instance.report = self.report
        form.instance.lead_type = 'PURCHASE'
        form.instance.license_type = self.license_type
        
        # Sync full_name
        first = form.cleaned_data.get('first_name', '')
        last = form.cleaned_data.get('last_name', '')
        form.instance.full_name = f"{first} {last}".strip()
        
        self.object = form.save()

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.POST.get('ajax') == 'true':
            return JsonResponse({
                'status': 'success',
                'lead_id': self.object.id,
                'message': 'Details saved. Please proceed with payment.'
            })
        
        # Original flow for non-ajax
        threading.Thread(target=send_lead_emails_task, args=(self.object,)).start()
        messages.success(self.request, "Your order has been placed successfully! We will contact you shortly.")
            
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('report-detail', kwargs={'slug': self.report.slug})

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors in the form.")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field.capitalize()}: {error}")
        return super().form_invalid(form)

class ContactFormView(CreateView):
    model = Lead
    form_class = LeadForm
    template_name = 'pages/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_title'] = 'Contact Us - Markets NXT'
        context['meta_description'] = 'Get in touch with Markets NXT for market intelligence, strategic advisory, and custom research engagements.'
        return context
    
    def form_valid(self, form):
        form.instance.lead_type = 'CONTACT'
        
        # Sync full_name
        first = form.cleaned_data.get('first_name', '')
        last = form.cleaned_data.get('last_name', '')
        form.instance.full_name = f"{first} {last}".strip()
        
        response = super().form_valid(form)
        
        # Async Email Sending
        threading.Thread(target=send_lead_emails_task, args=(self.object,)).start()
        messages.success(self.request, "Thank you for contacting us! We will get back to you shortly.")
            
        return redirect('pages:contact')

    def get_success_url(self):
        return reverse('pages:contact')

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors in the form.")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field.capitalize()}: {error}")
        return super().form_invalid(form)

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(csrf_exempt, name='dispatch')
class CapturePaymentView(View):
    """
    Handles capturing the payment after user approves it on the PayPal side.
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            order_id = data.get('orderID')
            lead_id = data.get('leadID')

            if not order_id or not lead_id:
                return JsonResponse({'status': 'error', 'message': 'Missing orderID or leadID'}, status=400)

            # Retrieve the lead
            lead = get_object_or_404(Lead, id=lead_id)
            
            # Here we would normally verify the payment with PayPal API
            # For now, we mark the lead as paid and trigger emails
            lead.message = f"{lead.message}\n\n[PAYPAL ORDER ID: {order_id}]"
            lead.save()

            # Trigger emails in background
            threading.Thread(target=send_lead_emails_task, args=(lead,)).start()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"PayPal capture error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class NewsletterSubscribeAPIView(generics.CreateAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if already subscribed to prevent duplicates
        if Lead.objects.filter(email__iexact=email, lead_type='NEWSLETTER').exists():
            return Response({'message': 'You are already subscribed!'}, status=status.HTTP_200_OK)
        
        data = {
            'email': email,
            'lead_type': 'NEWSLETTER',
            'message': 'Subscribed via Sidebar Widget'
        }
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({'message': 'Subscribed successfully'}, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        lead = serializer.save()
        # Run email in thread
        threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
