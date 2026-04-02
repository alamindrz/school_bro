"""
Public Finance Views
========================

Public-facing payment endpoints.
"""

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..services import PaymentService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_http_methods(["POST"]), name="dispatch")
class PaystackWebhookView(View):
    """
    Secure Paystack webhook endpoint.
    Handles all Paystack webhook events.
    """
    
    def post(self, request, *args, **kwargs):
        # Verify signature
        if not PaymentService.verify_webhook(request):
            logger.warning("Invalid webhook signature.")
            return HttpResponse(status=401)
        
        try:
            payload = json.loads(request.body)
            event = payload.get("event")
            
            logger.info(f"Webhook received: {event}")
            
            # Process webhook
            result = PaymentService.handle_webhook(payload)
            
            return JsonResponse({"status": "success", "result": result})
            
        except Exception as e:
            logger.exception(f"Webhook processing error: {e}")
            return JsonResponse({"status": "error"}, status=200)