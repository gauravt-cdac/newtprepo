# reviews/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Review
from orders.models import Order, OrderItem
from products.models import Cake

@login_required
def add_review(request, order_id, cake_id):
    order = get_object_or_404(Order, id=order_id, user=request.user, status='delivered')
    cake = get_object_or_404(Cake, id=cake_id)
    
    # Check if user ordered this cake
    order_item = get_object_or_404(OrderItem, order=order, variant__cake=cake)
    
    # Check if review already exists
    if Review.objects.filter(user=request.user, cake=cake, order=order).exists():
        messages.error(request, 'You have already reviewed this cake for this order.')
        return redirect('order_detail', order_id=order.id)
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        title = request.POST.get('title')
        comment = request.POST.get('comment')
        
        Review.objects.create(
            user=request.user,
            cake=cake,
            order=order,
            rating=rating,
            title=title,
            comment=comment
        )
        
        messages.success(request, 'Review submitted successfully! It will be visible after admin approval.')
        return redirect('order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'cake': cake,
    }
    return render(request, 'reviews/add_review.html', context)

def cake_reviews(request, cake_id):
    cake = get_object_or_404(Cake, id=cake_id)
    reviews = cake.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Calculate average rating
    if reviews.exists():
        avg_rating = sum(review.rating for review in reviews) / reviews.count()
        avg_rating = round(avg_rating, 1)
    else:
        avg_rating = 0
    
    context = {
        'cake': cake,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'total_reviews': reviews.count(),
    }
    return render(request, 'reviews/cake_reviews.html', context)
