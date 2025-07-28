# orders/models.py
from django.db import models
from accounts.models import User, Address
from products.models import CakeVariant
from decimal import Decimal

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(CakeVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'variant']
    
    def get_total_price(self):
        return self.variant.price * self.quantity

class Coupon(models.Model):
    COUPON_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=20, unique=True)
    coupon_type = models.CharField(max_length=10, choices=COUPON_TYPES)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Optional: Seller-specific coupons
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                              limit_choices_to={'role': 'seller'})
    
    def is_valid(self, order_amount=None):
        from django.utils import timezone
        
        if not self.is_active:
            return False, "Coupon is not active"
        
        if timezone.now() < self.valid_from:
            return False, "Coupon is not yet valid"
            
        if timezone.now() > self.valid_until:
            return False, "Coupon has expired"
        
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit exceeded"
        
        if order_amount and order_amount < self.min_order_amount:
            return False, f"Minimum order amount is ₹{self.min_order_amount}"
        
        return True, "Valid"
    
    def calculate_discount(self, order_amount):
        if self.coupon_type == 'percentage':
            discount = (order_amount * self.value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return discount
        else:  # fixed
            return min(self.value, order_amount)

class Order(models.Model):
    STATUS_CHOICES = [
        ('placed', 'Order Placed'),
        ('confirmed', 'Confirmed'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('razorpay', 'Online Payment'),
        ('cod', 'Cash on Delivery'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    shipping_address = models.ForeignKey(Address, on_delete=models.PROTECT)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=50)
    coupon_discount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    is_paid = models.BooleanField(default=False)
    
    # Order tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='placed')
    estimated_delivery = models.DateField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Coupon
    applied_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f"CO{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def can_be_cancelled(self):
        return self.status in ['placed', 'confirmed', 'packed']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(CakeVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)  # Price at time of order
    
    def get_total_price(self):
        return self.price * self.quantity

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=15, choices=Order.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
