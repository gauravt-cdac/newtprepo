import logging
import razorpay
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from orders.models import Order

logger = logging.getLogger(__name__)

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        messages.info(request, "This order is already paid")
        return redirect("order_detail", order_id=order.id)

    try:
        razorpay_order = razorpay_client.order.create({
            "amount": int(order.total_amount * 100),  # amount in paise
            "currency": "INR",
            "payment_capture": "1",
        })
    except Exception as e:
        logger.error(f"Failed to create Razorpay order for order {order.order_number}: {e}")
        messages.error(request, "Failed to initiate payment. Please try again later.")
        return redirect("order_detail", order_id=order.id)

    order.razorpay_order_id = razorpay_order["id"]
    order.save()
    logger.debug(f"Razorpay order created: {razorpay_order['id']} for order {order.order_number}")

    context = {
        "order": order,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(order.total_amount * 100),
    }
    return render(request, "payments/payment_page.html", context)


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")

        logger.debug(f"Payment success called with razorpay_order_id={order_id}, "
                     f"razorpay_payment_id={payment_id}, signature={signature}")

        params = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }

        try:
            razorpay_client.utility.verify_payment_signature(params)
            logger.info(f"Payment signature verified for order {order_id}")

            order = Order.objects.get(razorpay_order_id=order_id)
            order.razorpay_payment_id = payment_id
            order.razorpay_signature = signature
            order.is_paid = True
            order.status = "confirmed"
            order.save()

            for item in order.items.all():
                variant = item.variant
                logger.debug(f"Reducing stock of variant {variant.id} by {item.quantity}")
                variant.stock = max(0, variant.stock - item.quantity)
                variant.save()

            from .utils import send_order_confirmation_email, generate_invoice_pdf

            try:
                send_order_confirmation_email(order)
                logger.debug(f"Order confirmation email sent for order {order.order_number}")
            except Exception as e:
                logger.error(f"Failed to send email for order {order.order_number}: {e}")

            try:
                generate_invoice_pdf(order)
                logger.debug(f"Invoice PDF generated for order {order.order_number}")
            except Exception as e:
                logger.error(f"Failed to generate invoice PDF for order {order.order_number}: {e}")

            return JsonResponse({"status": "Payment successful"})

        except razorpay.errors.SignatureVerificationError as sve:
            logger.error(f"Payment signature verification failed: {sve}")
            return JsonResponse({"status": "Payment verification failed"})

        except Order.DoesNotExist:
            logger.error(f"Order not found with razorpay_order_id={order_id}")
            return JsonResponse({"status": "Order not found"})

        except Exception as e:
            logger.error(f"Unexpected error in payment verification: {e}")
            return JsonResponse({"status": "Payment verification failed"})

    logger.warning(f"Invalid request method {request.method} for payment_success")
    return JsonResponse({"status": "Invalid request"})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "orders/order_success.html", {"order": order})
