from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import stripe
import json
import logging
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import Booking, Payment, StatusHistory

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error("Invalid payload", exc_info=True)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature", exc_info=True)
        return HttpResponse(status=400)

    # Handle payment events
    if event.type == 'payment_intent.succeeded':
        return handle_payment_succeeded(event)
    elif event.type == 'payment_intent.payment_failed':
        return handle_payment_failed(event)
    elif event.type == 'charge.refunded':
        return handle_refund_completed(event)

    return HttpResponse(status=200)

def handle_payment_succeeded(event):
    payment_intent = event.data.object

    try:
        with transaction.atomic():
            booking_id = payment_intent.metadata.get('booking_id')
            if not booking_id:
                logger.warning("No booking ID in payment_intent metadata")
                return HttpResponse(status=200)

            booking = Booking.objects.get(id=booking_id)

            # Update payment details
            Payment.objects.create(
                booking=booking,
                amount=payment_intent.amount / 100,
                currency=payment_intent.currency.upper(),
                payment_method='STRIPE',
                transaction_id=payment_intent.id,
                status='COMPLETED',
                transaction_date=timezone.now(),
                additional_details={
                    'transfer_cost': payment_intent.metadata.get('transfer_cost', 0),
                    'service_fee': payment_intent.metadata.get('service_fee', 0),
                    'service_fee_percentage': payment_intent.metadata.get('service_fee_percentage', 0),
                    'vehicle_type': payment_intent.metadata.get('vehicle_type', 'STANDARD')
                }
            )

            if booking.status == 'PENDING':
                booking.update_status('CONFIRMED')
                StatusHistory.objects.create(
                    booking=booking,
                    status='CONFIRMED',
                    changed_at=timezone.now(),
                    notes=f"Payment confirmed via webhook ({payment_intent.id})"
                )

    except Booking.DoesNotExist:
        logger.error(f"Booking not found: {booking_id}")
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {str(e)}", exc_info=True)

    return HttpResponse(status=200)

def handle_payment_failed(event):
    payment_intent = event.data.object

    try:
        booking_id = payment_intent.metadata.get('booking_id')
        if not booking_id:
            return HttpResponse(status=200)

        booking = Booking.objects.get(id=booking_id)
        booking.update_status('PAYMENT_FAILED')

        StatusHistory.objects.create(
            booking=booking,
            status='PAYMENT_FAILED',
            changed_at=timezone.now(),
            notes=f"Payment failed: {payment_intent.last_payment_error or 'Unknown error'}"
        )

    except Booking.DoesNotExist:
        logger.error(f"Booking not found: {booking_id}")
    except Exception as e:
        logger.error(f"Error handling payment failed: {str(e)}", exc_info=True)

    return HttpResponse(status=200)

def handle_refund_completed(event):
    charge = event.data.object

    try:
        payment = Payment.objects.get(transaction_id=charge.payment_intent)
        payment.status = 'REFUNDED'
        payment.additional_details.update({
            'refund_id': charge.id,
            'refund_amount': charge.amount_refunded / 100
        })
        payment.save()

        StatusHistory.objects.create(
            booking=payment.booking,
            status='REFUNDED',
            changed_at=timezone.now(),
            notes=f"Refund processed: {charge.id}"
        )

    except Payment.DoesNotExist:
        logger.error(f"Payment not found for charge: {charge.id}")
    except Exception as e:
        logger.error(f"Error handling refund: {str(e)}", exc_info=True)

    return HttpResponse(status=200)
