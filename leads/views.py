from django.views.generic.edit import CreateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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

def clean_paypal_payload(data):
    """
    Recursively remove None, empty strings, and empty objects from the payload.
    Ensures PayPal doesn't throw validation errors for empty fields.
    """
    if isinstance(data, dict):
        return {
            k: clean_paypal_payload(v) 
            for k, v in data.items() 
            if v not in [None, "", [], {}]
        }
    elif isinstance(data, list):
        return [
            clean_paypal_payload(i) 
            for i in data 
            if i not in [None, "", [], {}]
        ]
    return data

def set_paypal_stc(tracking_id, lead, access_token=None):
    """
    Invokes the RISK/STC (Set Transaction Context) API.
    https://developer.paypal.com/docs/limited-release/raas/v1/api/
    """
    try:
        token = access_token or get_paypal_access_token()
        if not token:
            return False
            
        base_url = get_paypal_base_url()
        # The endpoint for STC is /v1/risk/transaction-contexts/{tracking_id}
        url = f"{base_url}/v1/risk/transaction-contexts/{tracking_id}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Industry pack fields for Digital Goods
        stc_data = {
            "additional_data": [
                {"key": "sender_account_id", "value": str(lead.id)},
                {"key": "sender_first_name", "value": lead.first_name},
                {"key": "sender_last_name", "value": lead.last_name},
                {"key": "sender_email", "value": lead.email},
                {"key": "sender_phone", "value": lead.phone},
                {"key": "sender_country_code", "value": lead.country_code or "US"}
            ]
        }
        
        # Filter out empty values
        stc_data["additional_data"] = [
            item for item in stc_data["additional_data"] if item["value"]
        ]
        
        response = requests.put(url, headers=headers, json=stc_data, timeout=10)
        if response.status_code not in [200, 204]:
            logger.error(f"PayPal STC API failed ({response.status_code}): {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error in PayPal STC: {e}")
        return False


def get_paypal_base_url():
    mode = os.environ.get('PAYPAL_MODE', 'sandbox')
    return "https://api-m.paypal.com" if mode == 'live' else "https://api-m.sandbox.paypal.com"

def get_paypal_access_token():
    try:
        client_id = os.environ.get('PAYPAL_CLIENT_ID')
        client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')

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
            data={"grant_type": "client_credentials"},
            timeout=15  # ← prevent infinite hang
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

        base_url = get_paypal_base_url()
        url = f"{base_url}/v2/checkout/orders/{order_id}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        response = requests.get(url, headers=headers, timeout=15)  # ← timeout added
        if response.status_code != 200:
            return False, f"Could not retrieve order details: {response.text}"

        order_data = response.json()
        order_status = order_data.get('status')

        if order_status == 'COMPLETED':
            return True, None

        return False, f"Payment status is {order_status}, not COMPLETED"

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
        subject_user = "Thank you for contacting Markets NXT"
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

@method_decorator(csrf_exempt, name='dispatch')
class LeadCreateAPIView(generics.CreateAPIView):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    authentication_classes = [] # Disable CSRF/Session enforcement
    permission_classes = []      # Allow public lead creation

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in LeadCreateAPIView: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def perform_create(self, serializer):
        logger.info(f"Creating lead from API: {serializer.validated_data.get('email')}")
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
        # Pre-truncate title to 5 words so the template doesn't need a filter tag
        words = self.report.title.split()
        context['short_title'] = ' '.join(words[:5]) + (' ...' if len(words) > 5 else '')
        
        # Determine Title based on URL or Type
        url_name = self.request.resolver_match.url_name
        if 'sample' in url_name:
            context['page_title'] = "Request Sample"
            context['lead_type_code'] = "SAMPLE"
        elif 'discount' in url_name:
            context['page_title'] = "Ask for Discount"
            context['lead_type_code'] = "DISCOUNT"
        elif 'customization' in url_name:
            context['page_title'] = "Request Customization"
            context['lead_type_code'] = "CUSTOMIZATION"
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
    """
    Handles checkout flow:
    - GET: Shows checkout form
    - POST: Processes form and creates lead
    """
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        license_type = kwargs.get('license_type')
        
        # If accessing /checkout/slug/?license=... redirect to clean /checkout/slug/license/
        if not license_type and request.GET.get('license'):
            lt = request.GET.get('license')
            if lt == 'data': lt = 'datapack'
            return redirect('checkout', slug=slug, license_type=lt)
            
        # Standard lookup
        if not license_type:
            # Fallback if somehow they hit /checkout/slug/ with neither path nor query
            messages.error(request, "Please select a license type.")
            return redirect('report-detail', slug=slug)

        # Mapping datapack URL slug to internal 'data' license mode
        if license_type == 'datapack':
            license_type = 'data'
            
        report = get_object_or_404(Report, slug=slug)
        
        # Calculate Price
        price = 0
        license_label = ''
        if license_type == 'single':
            price = report.single_user_price
            license_label = 'Single User License'
        elif license_type == 'multi':
            price = report.multi_user_price
            license_label = 'Multi User License'
        elif license_type == 'enterprise':
            price = report.enterprise_price
            license_label = 'Enterprise License'
        elif license_type == 'data':
            price = report.data_pack_price
            license_label = 'Data Pack License'
        
        if not price:
            messages.error(request, "Please select a license type.")
            # If no price, we go back to report-detail.
            return redirect('report-detail', slug=slug)
        
        # Create form
        from .forms import CheckoutForm
        form = CheckoutForm()
        
        context = {
            'form': form,
            'report': report,
            'license_type': license_type,
            'license_label': license_label,
            'price': price,
            # Only show dev bypass button when in sandbox mode AND DEBUG=True
            'debug': settings.DEBUG and os.environ.get('PAYPAL_MODE', 'sandbox') != 'live',
        }
        
        return render(request, 'leads/checkout.html', context)
    
    def post(self, request, *args, **kwargs):
        """
        Process checkout form submission
        """
        slug = kwargs.get('slug')
        license_type = kwargs.get('license_type') or request.POST.get('license') or request.GET.get('license')
        
        if license_type == 'datapack':
            license_type = 'data'
            
        report = get_object_or_404(Report, slug=slug)
        
        # Calculate Price
        price = 0
        if license_type == 'single': price = report.single_user_price
        elif license_type == 'multi': price = report.multi_user_price
        elif license_type == 'enterprise': price = report.enterprise_price
        elif license_type == 'data': price = report.data_pack_price
        
        if not price:
            return JsonResponse({'status': 'error', 'message': 'Invalid price'}, status=400)
        
        # Check if AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax')
        
        from .forms import CheckoutForm
        form = CheckoutForm(request.POST)
        
        if form.is_valid():
            # Create Lead
            lead = form.save(commit=False)
            lead.report = report
            lead.license_type = license_type
            lead.lead_type = 'PURCHASE'
            lead.ip_address = request.META.get('REMOTE_ADDR')
            
            # Sync full_name
            lead.full_name = f"{lead.first_name} {lead.last_name}".strip()
            lead.save()
            
            if is_ajax:
                # Return lead_id for frontend to initiate payment
                return JsonResponse({
                    'status': 'success',
                    'lead_id': lead.id,
                    'message': 'Details saved successfully'
                })
            else:
                # Non-AJAX fallback (shouldn't happen normally)
                messages.success(request, "Details saved. Redirecting to payment...")
                return redirect('report-detail', slug=slug)
        else:
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please correct the errors in the form',
                    'errors': form.errors
                }, status=400)
            else:
                messages.error(request, "Please correct the errors in the form.")
                # Map back to URL slug
                url_license = license_type
                if url_license == 'data': url_license = 'datapack'
                return redirect('checkout', slug=slug, license_type=url_license)

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

            # Get price from license type
            price = 0
            if lead.license_type == 'single':     price = lead.report.single_user_price
            elif lead.license_type == 'multi':    price = lead.report.multi_user_price
            elif lead.license_type == 'enterprise': price = lead.report.enterprise_price
            elif lead.license_type == 'data':     price = lead.report.data_pack_price

            if not price:
                return JsonResponse({'error': 'Invalid price configuration'}, status=400)

            token = get_paypal_access_token()
            if not token:
                logger.error("PayPal auth failed when creating order")
                return JsonResponse({'error': 'Failed to authenticate with PayPal. Please try again.'}, status=500)

            base_url = get_paypal_base_url()
            url = f"{base_url}/v2/checkout/orders"

            # Construct return URLs — use HTTPS in production via SECURE_PROXY_SSL_HEADER
            host = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
            return_url = f"{protocol}://{host}/api/leads/paypal-return/?lead_id={lead.id}"
            cancel_url  = f"{protocol}://{host}/api/leads/paypal-cancel/?lead_id={lead.id}"

            # Format price correctly for PayPal (must be string with 2 decimal places)
            price_str = "{:.2f}".format(float(price))

            # Generate Tracking ID for STC (Risk assessment)
            # This will be passed back in return_url to be used in capture
            tracking_id = f"MNXT-TRK-{lead.id}-{uuid.uuid4().hex[:6]}"
            set_paypal_stc(tracking_id, lead, access_token=token)

            # Construct return URLs — use HTTPS in production via SECURE_PROXY_SSL_HEADER
            host = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
            return_url = f"{protocol}://{host}/api/leads/paypal-return/?lead_id={lead.id}&tracking_id={tracking_id}"
            cancel_url  = f"{protocol}://{host}/api/leads/paypal-cancel/?lead_id={lead.id}"

            payload = {
                "intent": "CAPTURE",
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "brand_name": "Markets NXT",
                            "shipping_preference": "NO_SHIPPING",
                            "user_action": "PAY_NOW",
                            "return_url": return_url,
                            "cancel_url": cancel_url,
                            "payment_method_selected": "PAYPAL",
                            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED"
                        },
                        "email_address": lead.email,
                        "name": {
                            "given_name": lead.first_name,
                            "surname": lead.last_name
                        },
                        "phone": {
                            "phone_number": {
                                "national_number": lead.phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '') if lead.phone else None
                            }
                        }
                    }
                },
                "purchase_units": [{
                    "reference_id": f"lead-{lead.id}",
                    "amount": {
                        "currency_code": "USD",
                        "value": price_str,
                        "breakdown": {
                            "item_total": {
                                "currency_code": "USD",
                                "value": price_str
                            }
                        }
                    },
                    "items": [{
                        "name": lead.report.title[:127],
                        "description": f"{lead.get_license_type_display()} License",
                        "quantity": "1",
                        "unit_amount": {
                            "currency_code": "USD",
                            "value": price_str
                        },
                        "category": "DIGITAL_GOODS"
                    }],
                    "soft_descriptor": "Markets NXT",
                    "invoice_id": f"MNXT-{lead.id}-{uuid.uuid4().hex[:6].upper()}"
                }]
            }

            # Remove null/empty values to prevent PayPal validation errors
            payload = clean_paypal_payload(payload)

            # --- DEBUG LOGGING FOR LOCAL TESTING ---
            logger.info("--- PAYPAL CREATE ORDER PAYLOAD ---")
            logger.info(json.dumps(payload, indent=2))
            # ----------------------------------------

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                # Unique Id for each transaction attempt
                "PayPal-Request-Id": str(uuid.uuid4())
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            # --- DEBUG LOGGING FOR LOCAL TESTING ---
            logger.info(f"--- PAYPAL CREATE ORDER RESPONSE ({response.status_code}) ---")
            logger.info(response.text)
            # ----------------------------------------

            if response.status_code in [200, 201]:
                order_data = response.json()
                links = order_data.get('links', [])
                
                # Modern flows with payment_source often use 'payer-action' instead of 'approve'
                # We check for both to ensure compatibility
                approve_url = next((link['href'] for link in links if link['rel'] in ['approve', 'payer-action']), None)

                if approve_url:
                    return JsonResponse({'approve_url': approve_url})
                else:
                    logger.error(f"No usable redirect link found in PayPal response: {order_data}")
                    return JsonResponse({'error': 'No payment redirect link found from PayPal'}, status=500)
            else:
                logger.error(f"PayPal Order Creation Failed ({response.status_code}): {response.text}")
                return JsonResponse({'error': 'Failed to create PayPal order. Please try again.'}, status=500)

        except Exception as e:
            logger.error(f"Error creating PayPal order: {e}", exc_info=True)
            return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)

class PayPalReturnView(View):
    def get(self, request, *args, **kwargs):
        lead_id = request.GET.get('lead_id')
        token   = request.GET.get('token')  # PayPal Order ID

        if not lead_id or not token:
            logger.error(f"PayPal return missing params: lead_id={lead_id}, token={token}")
            return redirect('/')

        try:
            lead = get_object_or_404(Lead, id=lead_id)

            # ── Idempotency guard: already captured? Redirect straight to success ──
            if '[CAPTURED]' in (lead.message or ''):
                logger.info(f"Lead {lead_id} already captured — skipping duplicate capture")
                return redirect(reverse('report-detail', kwargs={'slug': lead.report.slug}) + "?payment=success")

            # ── Get access token ──
            access_token = get_paypal_access_token()
            if not access_token:
                logger.error("PayPal auth failed during capture")
                # Map back to URL slug
                url_license = lead.license_type
                if url_license == 'data': url_license = 'datapack'
                return redirect(reverse('checkout', kwargs={'slug': lead.report.slug, 'license_type': url_license}) + "?payment=failed")

            base_url = get_paypal_base_url()
            url = f"{base_url}/v2/checkout/orders/{token}/capture"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
                # Unique Id for each capture attempt
                "PayPal-Request-Id": str(uuid.uuid4()),
            }
            
            # Pass the tracking_id from the STC/RISK API call if available
            tracking_id = request.GET.get('tracking_id')
            if tracking_id:
                headers["PayPal-Client-Metadata-Id"] = tracking_id

            # --- DEBUG LOGGING FOR LOCAL TESTING ---
            logger.info("--- PAYPAL CAPTURE REQUEST HEADERS ---")
            logger.info(headers)
            # ----------------------------------------

            response = requests.post(url, headers=headers, json={}, timeout=30)
            
            # --- DEBUG LOGGING FOR LOCAL TESTING ---
            logger.info(f"--- PAYPAL CAPTURE RESPONSE ({response.status_code}) ---")
            logger.info(response.text)
            # ----------------------------------------

            # ── SUCCESS ──
            if response.status_code in [200, 201]:
                capture_data = response.json()
                
                # Ensure the capture status is COMPLETED
                purchase_units = capture_data.get('purchase_units', [])
                capture_status = None
                if purchase_units:
                    payments = purchase_units[0].get('payments', {})
                    captures = payments.get('captures', [])
                    if captures:
                        capture_status = captures[0].get('status')
                
                if capture_status != 'COMPLETED':
                    logger.error(f"PayPal Order {token} failed: Status is {capture_status}")
                    url_license = lead.license_type
                    if url_license == 'data': url_license = 'datapack'
                    return redirect(reverse('checkout', kwargs={'slug': lead.report.slug, 'license_type': url_license}) + f"?payment=failed&reason={capture_status}")

                payer = capture_data.get('payer', {})
                lead.message = f"{lead.message}\n\n[PAYPAL ORDER ID: {token}] [CAPTURED]"

                if payer:
                    lead.email      = payer.get('email_address', lead.email)
                    lead.first_name = payer.get('name', {}).get('given_name', lead.first_name)
                    lead.last_name  = payer.get('name', {}).get('surname',    lead.last_name)
                    lead.full_name  = f"{lead.first_name} {lead.last_name}".strip()

                    purchase_units = capture_data.get('purchase_units', [])
                    if purchase_units:
                        address = purchase_units[0].get('shipping', {}).get('address', {})
                        if address:
                            lead.address  = address.get('address_line_1', lead.address)
                            lead.city     = address.get('admin_area_2',   lead.city)
                            lead.state    = address.get('admin_area_1',   lead.state)
                            lead.zip_code = address.get('postal_code',    lead.zip_code)
                            lead.country  = address.get('country_code',   lead.country)

                lead.save()
                threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
                return redirect(reverse('report-detail', kwargs={'slug': lead.report.slug}) + "?payment=success")

            # ── 422: Already captured (e.g. user refreshed) → treat as success ──
            elif response.status_code == 422:
                logger.warning(f"PayPal 422 for lead {lead_id} order {token} — already captured, treating as success")
                if '[CAPTURED]' not in (lead.message or ''):
                    lead.message = f"{lead.message}\n\n[PAYPAL ORDER ID: {token}] [CAPTURED-DUPLICATE]"
                    lead.save()
                    threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
                return redirect(reverse('report-detail', kwargs={'slug': lead.report.slug}) + "?payment=success")

            # ── Any other failure → back to checkout with error flag ──
            else:
                logger.error(f"PayPal capture failed ({response.status_code}): {response.text}")
                # Map back to URL slug
                url_license = lead.license_type
                if url_license == 'data': url_license = 'datapack'
                return redirect(reverse('checkout', kwargs={'slug': lead.report.slug, 'license_type': url_license}) + "?payment=failed")

        except Exception as e:
            logger.error(f"PayPalReturnView unexpected error: {e}", exc_info=True)
            return redirect('/')

class PayPalCancelView(View):
    def get(self, request, *args, **kwargs):
        lead_id = request.GET.get('lead_id')
        try:
            lead = get_object_or_404(Lead, id=lead_id)
            # Map back to URL slug
            url_license = lead.license_type
            if url_license == 'data': url_license = 'datapack'
            return redirect(reverse('checkout', kwargs={'slug': lead.report.slug, 'license_type': url_license}) + "?payment=cancelled")
        except Exception:
            return redirect('/')

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
            
        captcha = request.data.get('captcha')
        # Check if already subscribed to prevent duplicates
        if Lead.objects.filter(email__iexact=email, lead_type='NEWSLETTER').exists():
            return Response({'message': 'You are already subscribed!'}, status=status.HTTP_200_OK)
        
        data = {
            'email': email,
            'lead_type': 'NEWSLETTER',
            'message': 'Subscribed via Sidebar Widget',
            'captcha': captcha
        }
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({'message': 'Subscribed successfully'}, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        lead = serializer.save()
        # Run email in thread
        threading.Thread(target=send_lead_emails_task, args=(lead,)).start()
