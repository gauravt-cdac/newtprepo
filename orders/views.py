# orders/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings

from decimal import Decimal
import os

from .models import Cart, CartItem, Order, OrderItem, Coupon
from products.models import CakeVariant
from accounts.models import Address


@login_required
def add_to_cart(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))

        variant = get_object_or_404(CakeVariant, id=variant_id)

        if quantity > variant.stock:
            return JsonResponse({'success': False, 'message': 'Insufficient stock'})

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                return JsonResponse({'success': False, 'message': 'Insufficient stock'})
            cart_item.quantity = new_quantity
            cart_item.save()

        return JsonResponse({
            'success': True,
            'message': 'Added to cart successfully',
            'cart_count': cart.get_total_items()
        })

    # For non-POST or invalid requests
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def cart_detail(request):
    try:
        cart = request.user.cart
        cart_items = cart.items.select_related('variant__cake').all()
    except Cart.DoesNotExist:
        cart = None
        cart_items = []

    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'orders/cart_detail.html', context)


@login_required
@require_POST
def update_cart_item(request):
    cart_item_id = request.POST.get('cart_item_id')
    quantity = int(request.POST.get('quantity'))

    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)

    if quantity <= 0:
        cart_item.delete()
        return JsonResponse({'success': True, 'message': 'Item removed from cart'})

    if quantity > cart_item.variant.stock:
        return JsonResponse({'success': False, 'message': 'Insufficient stock'})

    cart_item.quantity = quantity
    cart_item.save()

    return JsonResponse({
        'success': True,
        'message': 'Cart updated',
        'item_total': float(cart_item.get_total_price()),
        'cart_total': float(cart_item.cart.get_total_price())
    })


@login_required
def checkout(request):
    try:
        cart = request.user.cart
        if not cart.items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('cart_detail')
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty')
        return redirect('cart_detail')

    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method')
        coupon_code = request.POST.get('coupon_code', '').strip()

        address = get_object_or_404(Address, id=address_id, user=request.user)

        subtotal = cart.get_total_price()
        delivery_charge = Decimal('50.00')  # Fixed delivery charge
        coupon_discount = Decimal('0.00')
        applied_coupon = None

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code)
                is_valid, message = coupon.is_valid(subtotal)
                if is_valid:
                    coupon_discount = coupon.calculate_discount(subtotal)
                    applied_coupon = coupon
                else:
                    messages.error(request, f"Coupon error: {message}")
                    return redirect('checkout')
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid coupon code")
                return redirect('checkout')

        total_amount = subtotal + delivery_charge - coupon_discount

        # Create order
        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            coupon_discount=coupon_discount,
            total_amount=total_amount,
            payment_method=payment_method,
            applied_coupon=applied_coupon
        )

        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                price=cart_item.variant.price
            )

        # Update coupon usage count
        if applied_coupon:
            applied_coupon.used_count += 1
            applied_coupon.save()

        # Clear cart
        cart.items.all().delete()

        if payment_method == 'razorpay':
            return redirect('initiate_payment', order_id=order.id)
        else:  # COD
            order.status = 'confirmed'
            order.save()
            # TODO: send order confirmation email here
            messages.success(request, 'Order placed successfully!')
            return redirect('order_success', order_id=order.id)

    addresses = request.user.addresses.all()

    context = {
        'cart': cart,
        'addresses': addresses,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_list(request):
    """
    List all orders of the logged-in buyer, ordered by newest first.
    """
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_list.html', context)


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Handle order cancellation POST request
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cancel_order':
            if order.can_be_cancelled():
                reason = request.POST.get('cancel_reason', '').strip()
                if reason:
                    order.status = 'cancelled'
                    order.save()
                    # Optionally: send email notification about cancellation here
                    messages.success(request, 'Order cancelled successfully.')
                    # Refund logic can be added if applicable
                    return redirect('order_list')
                else:
                    messages.error(request, 'Cancellation reason required.')
            else:
                messages.error(request, 'Order cannot be cancelled at this stage.')
    
    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if not order.is_paid:
        # Restrict invoice download before payment completion
        raise Http404("Invoice not available for unpaid orders")
    
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'invoices', f'invoice_{order.order_number}.pdf')
    if not os.path.exists(pdf_path):
        raise Http404("Invoice file not found")
    
    return FileResponse(open(pdf_path, 'rb'), content_type='application/pdf', 
                        as_attachment=True, filename=f'invoice_{order.order_number}.pdf')


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not order.can_be_cancelled():
        messages.error(request, "Order cannot be cancelled at this stage.")
        return redirect('order_detail', order_id=order.id)

    if request.method == "POST":
        reason = request.POST.get('cancel_reason', '')  # Can be saved/logged if needed
        order.status = 'cancelled'
        order.save()
        # TODO: add notification, refund logic if applicable
        messages.success(request, "Order cancelled successfully.")
        return redirect('order_list')

    return render(request, 'orders/cancel_order.html', {'order': order})
