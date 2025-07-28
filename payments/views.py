# payments/views.py
import razorpay
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from orders.models import Order
from django.shortcuts import render
from products.models import Cake, Category

import json

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.is_paid:
        messages.info(request, 'This order is already paid')
        return redirect('order_detail', order_id=order.id)
    
    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        'amount': int(order.total_amount * 100),  # Amount in paise
        'currency': 'INR',
        'payment_capture': '1'
    })
    
    # Save Razorpay order ID
    order.razorpay_order_id = razorpay_order['id']
    order.save()
    
    context = {
        'order': order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'amount': int(order.total_amount * 100),
    }
    return render(request, 'payments/payment_page.html', context)

@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        try:
            # Get payment details from Razorpay
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Update order
            order = Order.objects.get(razorpay_order_id=order_id)
            order.razorpay_payment_id = payment_id
            order.razorpay_signature = signature
            order.is_paid = True
            order.status = 'confirmed'
            order.save()
            
            # Update stock for ordered items
            for item in order.items.all():
                variant = item.variant
                variant.stock -= item.quantity
                variant.save()
            
            # Send confirmation email and generate PDF invoice
            from .utils import send_order_confirmation_email, generate_invoice_pdf
            send_order_confirmation_email(order)
            generate_invoice_pdf(order)
            
            return JsonResponse({'status': 'Payment successful'})
            
        except Exception as e:
            return JsonResponse({'status': 'Payment verification failed'})
    
    return JsonResponse({'status': 'Invalid request'})

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {'order': order}
    return render(request, 'orders/order_success.html', context)
