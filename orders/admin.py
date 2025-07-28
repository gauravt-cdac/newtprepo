# orders/admin.py
from django.contrib import admin
from .models import Cart, CartItem, Coupon, Order, OrderItem, OrderStatusHistory

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__username']
    inlines = [CartItemInline]

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'coupon_type', 'value', 'min_order_amount', 'valid_from', 'valid_until', 'usage_limit', 'used_count', 'is_active', 'seller']
    list_filter = ['coupon_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'seller__username']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price', 'quantity', 'variant')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'payment_method', 'total_amount', 'is_paid', 'created_at']
    list_filter = ['status', 'payment_method', 'is_paid', 'created_at']
    search_fields = ['order_number', 'user__email']
    inlines = [OrderItemInline]
    readonly_fields = ('order_number', 'subtotal', 'delivery_charge', 'coupon_discount', 'total_amount', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'updated_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number', 'updated_by__username']
