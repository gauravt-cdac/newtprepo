# products/admin.py
from django.contrib import admin
from .models import Category, Cake, CakeVariant, CakeImage

class CakeImageInline(admin.TabularInline):
    model = CakeImage
    extra = 1
    readonly_fields = ('created_at',)

class CakeVariantInline(admin.TabularInline):
    model = CakeVariant
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description']

@admin.register(Cake)
class CakeAdmin(admin.ModelAdmin):
    list_display = ['title', 'seller', 'category', 'dietary', 'is_active', 'is_todays_special', 'created_at', 'updated_at']
    list_filter = ['category', 'dietary', 'is_active', 'is_todays_special', 'created_at']
    search_fields = ['title', 'description', 'tags', 'flavor']
    inlines = [CakeVariantInline, CakeImageInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.role == 'admin':
            return qs
        if request.user.role == 'seller':
            return qs.filter(seller=request.user)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        if not change and request.user.role == 'seller':
            obj.seller = request.user
        super().save_model(request, obj, form, change)
