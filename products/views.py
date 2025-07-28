# products/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from accounts.decorators import seller_required
from .models import Cake, Category, CakeVariant
from django.shortcuts import render
from .models import Cake, Category

def cake_list(request):
    cakes = Cake.objects.filter(is_active=True).select_related('seller', 'category')
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        cakes = cakes.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search) |
            Q(flavor__icontains=search)
        )
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        cakes = cakes.filter(category_id=category_id)
    
    # Filter by dietary preference
    dietary = request.GET.get('dietary')
    if dietary:
        cakes = cakes.filter(dietary=dietary)
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price or max_price:
        variants = CakeVariant.objects.all()
        if min_price:
            variants = variants.filter(price__gte=min_price)
        if max_price:
            variants = variants.filter(price__lte=max_price)
        cake_ids = variants.values_list('cake_id', flat=True)
        cakes = cakes.filter(id__in=cake_ids)
    
    # Pagination
    paginator = Paginator(cakes, 12)  # 12 cakes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'dietary_choices': Cake.DIETARY_CHOICES,
        'current_filters': {
            'search': search,
            'category': category_id,
            'dietary': dietary,
            'min_price': min_price,
            'max_price': max_price,
        }
    }
    return render(request, 'products/cake_list.html', context)

def cake_detail(request, cake_id):
    cake = get_object_or_404(Cake, id=cake_id, is_active=True)
    variants = cake.variants.all()
    related_cakes = Cake.objects.filter(
        category=cake.category, 
        is_active=True
    ).exclude(id=cake.id)[:4]
    
    context = {
        'cake': cake,
        'variants': variants,
        'related_cakes': related_cakes,
    }
    return render(request, 'products/cake_detail.html', context)

@seller_required
def seller_dashboard(request):
    cakes = Cake.objects.filter(seller=request.user)
    context = {
        'cakes': cakes,
        'total_cakes': cakes.count(),
        'active_cakes': cakes.filter(is_active=True).count(),
    }
    return render(request, 'dashboard/seller_dashboard.html', context)

def home(request):
    # Show featured cakes, e.g. today's special or latest
    todays_special_cakes = Cake.objects.filter(is_todays_special=True, is_active=True)[:5]
    latest_cakes = Cake.objects.filter(is_active=True).order_by('-created_at')[:10]
    
    context = {
        'todays_special_cakes': todays_special_cakes,
        'latest_cakes': latest_cakes,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'products/home.html', context)