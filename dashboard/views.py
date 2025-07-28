# dashboard/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import admin_required, seller_required
from accounts.models import User, LoginActivity
from products.models import Cake
from orders.models import Order, OrderItem
from reviews.models import Review

@admin_required
def admin_dashboard(request):
    # Overall statistics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(is_paid=True).aggregate(
        total=Sum('total_amount'))['total'] or 0
    total_customers = User.objects.filter(role='buyer').count()
    pending_sellers = User.objects.filter(role='seller', is_approved=False).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Top selling cakes
    top_cakes = OrderItem.objects.values(
        'variant__cake__title'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_quantity')[:5]
    
    # Pending reviews
    pending_reviews = Review.objects.filter(is_approved=False).count()
    
    # Monthly revenue (last 6 months)
    monthly_revenue = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        revenue = Order.objects.filter(
            is_paid=True,
            created_at__gte=month_start,
            created_at__lt=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        monthly_revenue.append({
            'month': month_start.strftime('%B %Y'),
            'revenue': revenue
        })
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'pending_sellers': pending_sellers,
        'recent_orders': recent_orders,
        'top_cakes': top_cakes,
        'pending_reviews': pending_reviews,
        'monthly_revenue': monthly_revenue,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@admin_required
def seller_approval(request):
    pending_sellers = User.objects.filter(role='seller', is_approved=False)
    
    if request.method == 'POST':
        seller_id = request.POST.get('seller_id')
        action = request.POST.get('action')
        
        seller = get_object_or_404(User, id=seller_id, role='seller')
        
        if action == 'approve':
            seller.is_approved = True
            seller.save()
            # Send approval email
            messages.success(request, f'Seller {seller.username} approved successfully.')
        elif action == 'reject':
            seller.delete()  # Or set inactive
            messages.success(request, f'Seller application rejected.')
        
        return redirect('seller_approval')
    
    context = {'pending_sellers': pending_sellers}
    return render(request, 'dashboard/seller_approval.html', context)

@admin_required
def review_approval(request):
    pending_reviews = Review.objects.filter(is_approved=False).select_related(
        'user', 'cake', 'order'
    ).order_by('-created_at')
    
    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        action = request.POST.get('action')
        
        review = get_object_or_404(Review, id=review_id)
        
        if action == 'approve':
            review.is_approved = True
            review.save()
            messages.success(request, 'Review approved successfully.')
        elif action == 'reject':
            review.delete()
            messages.success(request, 'Review rejected.')
        
        return redirect('review_approval')
    
    context = {'pending_reviews': pending_reviews}
    return render(request, 'dashboard/review_approval.html', context)

@seller_required
def seller_dashboard(request):
    # Seller's statistics
    seller_cakes = Cake.objects.filter(seller=request.user)
    total_orders = OrderItem.objects.filter(variant__cake__seller=request.user).count()
    total_revenue = OrderItem.objects.filter(
        variant__cake__seller=request.user,
        order__is_paid=True
    ).aggregate(total=Sum('price'))['total'] or 0
    
    # Recent orders for seller's cakes
    recent_orders = OrderItem.objects.filter(
        variant__cake__seller=request.user
    ).select_related('order', 'variant__cake').order_by('-order__created_at')[:10]
    
    context = {
        'total_cakes': seller_cakes.count(),
        'active_cakes': seller_cakes.filter(is_active=True).count(),
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
    }
    return render(request, 'dashboard/seller_dashboard.html', context)
