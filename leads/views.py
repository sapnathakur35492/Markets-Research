from django.views.generic.edit import CreateView
from django.views import View
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
import requests
import base64
import uuid

logger = logging.getLogger(__name__)

def get_paypal_base_url():
    mode = os.environ.get('PAYPAL_MODE', 'sandbox')
    return "https://api-m.paypal.com" if mode == 'live' else "https://api-m.sandbox.paypal.com"

def get_paypal_access_token():
    try:
        client_id = os.environ.get('PAYPAL_CLIENT_ID')
        client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
        mode = os.environ.get('PAYPAL_MODE', 'sandbox')
        
        base_url = get_paypal_base_url()
        url = f"{base_url}/v1/oauth2/token"
        
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }
        
        response = requests.post(
            url, 
            auth=(client_id, client_secret), 
            headers=headers, 
            data={"grant_type": "client_credentials"}
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            logger.error(f"Failed to get PayPal Access Token: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error getting PayPal Token: {e}")
        return None

def verify_paypal_payment(order_id):
    """
    Verifies that the PayPal order is actually completed/approved.
    Returns (True, None) if valid, (False, error_message) if invalid.
    """
    try:
        token = get_paypal_access_token()
        if not token:
            return False, "Could not authenticate with Payment Gateway"

        mode = os.environ.get('PAYPAL_MODE', 'sandbox')
        base_url = get_paypal_base_url()
        url = f"{base_url}/v2/checkout/orders/{order_id}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return False, f"Could not retrieve order details: {response.text}"
            
        order_data = response.json()
        status = order_data.get('status')
        
        # Valid statuses for a captured/approved payment depending on flow
        # COMPLETED: Payment has been captured.
        # APPROVED: Payment is approved but not yet captured (if we were doing server-side capture).
        # Since client-side captures, we look for COMPLETED.
        if status == 'COMPLETED':
            return True, None
        
        return False, f"Payment status is {status}, not COMPLETED"
        
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        return False, str(e)

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
             subject_user = "Order Confirmation - MarketsNXT"
             message_user = f"Hi {full_name},\n\nThank you for your order of '{lead.report.title}'.\nWe have received your request for the {lead.get_license_type_display()} license.\nOur team will process your order and send you the download link shortly.\n\nBest Regards,\nTeam MarketsNXT"
        else:
            subject_user = "Thank You for Contacting MarketsNXT – We’ve Received Your Request"
            message_user = f"""Dear Valued Client,

Thank you for reaching out to MarketsNXT and submitting your requirements through our website. We appreciate your interest and the opportunity to support your business decisions with our research and advisory expertise.

MarketsNXT is a professional market intelligence and consulting firm with a strong legacy in delivering high-quality industry reports, custom research solutions, and strategic insights across global markets. 
MarketsNXT operates in strategic association with Montclaire and Stein, strengthening our global research capabilities and advisory network.

We operate with a strong focus on quality, data security, and process excellence, aligned with internationally recognized standards such as ISO 9001 for quality management and ISO 27001 for information security practices. This ensures that every client interaction, dataset, and deliverable is handled with structured quality controls and strict confidentiality.

Our offerings include:
* Industry and market research reports
* Custom research and consulting assignments
* Competitive intelligence studies
* Market sizing and forecasting
* Strategy and opportunity assessments
* Sector deep-dives and trend analysis

Please be assured that your requirements are in capable and experienced hands. Your inquiry has been successfully received and logged in our system.

One of our Business Managers will review your request and reach out to you shortly to understand your needs in more detail and guide you on the next steps.

We look forward to working with you.

Warm regards,
Team MarketsNXT
Client Relations Desk"""
            
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

class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        license_type = kwargs.get('license_type')
        report = get_object_or_404(Report, slug=slug)
        
        # Test Mode Logic (Dev Bypass)
        if settings.DEBUG and request.GET.get('test') == 'true':
            # Create Mock Lead
            lead = Lead.objects.create(
                report=report,
                license_type=license_type,
                lead_type='PURCHASE',
                email="test_user@example.com",
                full_name="Test User",
                first_name="Test",
                last_name="User",
                address="123 Test St",
                city="Test City",
                country="US",
                ip_address=request.META.get('REMOTE_ADDR'),
                message="[DEV BYPASS: PAYMENT SIMULATED]"
            )
            # Send Emails
            threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
            # Redirect to success
            messages.success(request, "Test Payment Successful!")
            return redirect(reverse('report-detail', kwargs={'slug': slug}) + "?payment=success")

        # Calculate Price
        price = 0
        if license_type == 'single': price = report.single_user_price
        elif license_type == 'multi': price = report.multi_user_price
        elif license_type == 'enterprise': price = report.enterprise_price
        elif license_type == 'data': price = report.data_pack_price
        
        if not price:
            messages.error(request, "Invalid license type or price.")
            return redirect('report-detail', slug=slug)

        # Create Temporary Lead
        temp_email = f"pending_{uuid.uuid4()}@temp.local"
        
        lead = Lead.objects.create(
            report=report,
            license_type=license_type,
            lead_type='PURCHASE',
            email=temp_email,
            full_name="Pending Payment",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Initiate PayPal Order
        token = get_paypal_access_token()
        if not token:
            print("ERROR: Failed to get PayPal Access Token") # Debug
            messages.error(request, "Payment gateway unavailable. Please try again.")
            return redirect('report-detail', slug=slug)

        base_url = get_paypal_base_url()
        url = f"{base_url}/v2/checkout/orders"
        
        host = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        return_url = f"{protocol}://{host}/api/leads/paypal-return/?lead_id={lead.id}"
        cancel_url = f"{protocol}://{host}/api/leads/paypal-cancel/?lead_id={lead.id}"

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(price),
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": str(price)
                        }
                    }
                },
                "description": f"{report.title} - {lead.get_license_type_display()}",
                "items": [{
                    "name": report.title[:120], # Max length limit
                    "unit_amount": {
                        "currency_code": "USD",
                        "value": str(price)
                    },
                    "quantity": "1",
                    "category": "DIGITAL_GOODS"
                }]
            }],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "brand_name": "Market Research",
                "user_action": "PAY_NOW",
                "shipping_preference": "NO_SHIPPING" # Don't require shipping for digital goods
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            print(f"DEBUG: Creating PayPal Order... URL: {url}")
            response = requests.post(url, headers=headers, json=payload)
            print(f"DEBUG: PayPal Response Status: {response.status_code}")
            print(f"DEBUG: PayPal Response Body: {response.text}")
            
            if response.status_code in [200, 201]:
                order_data = response.json()
                links = order_data.get('links', [])
                approve_url = next((link['href'] for link in links if link['rel'] == 'approve'), None)
                
                if approve_url:
                    return redirect(approve_url)
                else:
                    logger.error("No approve URL in PayPal response")
                    messages.error(request, "Error initiating payment with PayPal.")
                    return redirect('report-detail', slug=slug)
            else:
                logger.error(f"PayPal Order Creation Failed: {response.text}")
                messages.error(request, "Failed to connect to PayPal.")
                return redirect('report-detail', slug=slug)
        except Exception as e:
            logger.error(f"Error calling PayPal: {e}")
            print(f"DEBUG EXCEPTION: {e}")
            messages.error(request, "An unexpected error occurred.")
            return redirect('report-detail', slug=slug)

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
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

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
            
            # Verify Payment with PayPal
            is_valid, error = verify_paypal_payment(order_id)
            if not is_valid:
                 return JsonResponse({'status': 'error', 'message': f'Payment verification failed: {error}'}, status=400)

            # Mark as paid
            lead.message = f"{lead.message}\n\n[PAYPAL ORDER ID: {order_id}] [VERIFIED]"
            lead.save()

            # Trigger emails in background
            threading.Thread(target=send_lead_emails_task, args=(lead,)).start()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"PayPal capture error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CreatePayPalOrderView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            lead_id = data.get('lead_id')
            if not lead_id:
                return JsonResponse({'error': 'Missing lead_id'}, status=400)
                
            lead = get_object_or_404(Lead, id=lead_id)
            
            # licensing logic to get price
            price = 0
            if lead.license_type == 'single': price = lead.report.single_user_price
            elif lead.license_type == 'multi': price = lead.report.multi_user_price
            elif lead.license_type == 'enterprise': price = lead.report.enterprise_price
            elif lead.license_type == 'data': price = lead.report.data_pack_price
            
            if not price:
                return JsonResponse({'error': 'Invalid price configuration'}, status=400)

            token = get_paypal_access_token()
            if not token:
                return JsonResponse({'error': 'Failed to authenticate with PayPal'}, status=500)

            base_url = get_paypal_base_url()
            url = f"{base_url}/v2/checkout/orders"
            
            # Construct return URLs
            # In production these should be absolute URLs from settings or requesting host
            host = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
            return_url = f"{protocol}://{host}/api/leads/paypal-return/?lead_id={lead.id}"
            cancel_url = f"{protocol}://{host}/api/leads/paypal-cancel/?lead_id={lead.id}"

            payload = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": str(price)
                    },
                    "description": f"{lead.report.title} - {lead.get_license_type_display()}"
                }],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "brand_name": "Market Research",
                    "user_action": "PAY_NOW"
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                order_data = response.json()
                links = order_data.get('links', [])
                approve_url = next((link['href'] for link in links if link['rel'] == 'approve'), None)
                
                if approve_url:
                    return JsonResponse({'approve_url': approve_url})
                else:
                    return JsonResponse({'error': 'No approve link found from PayPal'}, status=500)
            else:
                logger.error(f"PayPal Order Creation Failed: {response.text}")
                return JsonResponse({'error': 'Failed to create PayPal order'}, status=500)
                
        except Exception as e:
            logger.error(f"Error creating PayPal order: {e}")
            return JsonResponse({'error': str(e)}, status=500)

class PayPalReturnView(View):
    def get(self, request, *args, **kwargs):
        lead_id = request.GET.get('lead_id')
        token = request.GET.get('token') # Order ID
        
        if not lead_id or not token:
             return HttpResponse("Missing details", status=400)
             
        # Capture the order
        access_token = get_paypal_access_token()
        base_url = get_paypal_base_url()
        url = f"{base_url}/v2/checkout/orders/{token}/capture"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.post(url, headers=headers)
        
        if response.status_code in [200, 201]:
             # Success
             lead = get_object_or_404(Lead, id=lead_id)
             lead.message = f"{lead.message}\n\n[PAYPAL ORDER ID: {token}] [CAPTURED]"
             
             # Fetch Payer Info from Captured Order
             # The capture response contains payer details
             capture_data = response.json()
             payer = capture_data.get('payer', {})
             
             # Update Lead Details from PayPal
             if payer:
                 lead.email = payer.get('email_address', lead.email)
                 lead.first_name = payer.get('name', {}).get('given_name', lead.first_name)
                 lead.last_name = payer.get('name', {}).get('surname', lead.last_name)
                 lead.full_name = f"{lead.first_name} {lead.last_name}".strip()
                 
                 # Address (if available in purchase_units)
                 purchase_units = capture_data.get('purchase_units', [])
                 if purchase_units:
                     shipping = purchase_units[0].get('shipping', {})
                     address = shipping.get('address', {})
                     if address:
                         lead.address = address.get('address_line_1', '')
                         lead.city = address.get('admin_area_2', '') # City
                         lead.state = address.get('admin_area_1', '') # State
                         lead.zip_code = address.get('postal_code', '')
                         lead.country = address.get('country_code', '')
             
             lead.save()
             
             threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
             
             return redirect(reverse('report-detail', kwargs={'slug': lead.report.slug}) + "?payment=success")
        else:
             logger.error(f"Capture failed: {response.text}")
             return HttpResponse("Payment capture failed. Please contact support.", status=500)

class PayPalCancelView(View):
    def get(self, request, *args, **kwargs):
        lead_id = request.GET.get('lead_id')
        lead = get_object_or_404(Lead, id=lead_id)
        # Redirect back to checkout or show message
        # We can't easily go back to checkout form with data pre-filled without session, 
        # so mostly redirect to report page or a cancel page.
        return redirect(reverse('checkout', kwargs={'slug': lead.report.slug, 'license_type': lead.license_type}) + "?payment=cancelled")

class DevBypassView(View):
    """
    Mock View to simulate a successful payment for testing purposes.
    Only available when DEBUG=True.
    """
    def post(self, request, *args, **kwargs):
        if not settings.DEBUG:
            return JsonResponse({'error': 'Dev tools disabled'}, status=403)
            
        try:
            data = json.loads(request.body)
            lead_id = data.get('lead_id')
            if not lead_id:
                return JsonResponse({'error': 'Missing lead_id'}, status=400)
            
            lead = get_object_or_404(Lead, id=lead_id)
            
            # Simulate generic payer info
            lead.email = "test_user@example.com"
            lead.first_name = "Test"
            lead.last_name = "User"
            lead.full_name = "Test User"
            lead.address = "123 Test St"
            lead.city = "Test City"
            lead.country = "US"
            lead.message = f"{lead.message}\n\n[DEV BYPASS: PAYMENT SIMULATED]"
            lead.save()
            
            threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
            
            # Return a fake approve_url that actually points to our return view
            # But wait, our return view expects a 'token' (Order ID) to capture.
            # We can't use the real return view because it calls PayPal capture.
            # So we should just return a "success" signal and let frontend redirect to success page.
            
            return JsonResponse({'status': 'success', 'redirect_url': reverse('report-detail', kwargs={'slug': lead.report.slug}) + "?payment=success"})
            
        except Exception as e:
            logger.error(f"Dev Bypass Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)

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
