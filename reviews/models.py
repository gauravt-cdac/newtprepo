# reviews/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from products.models import Cake
from orders.models import Order

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cake = models.ForeignKey(Cake, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(Order, on_delete=models.CASCADE)  # Can only review after purchase
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)  # Admin approval required
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'cake', 'order']  # One review per cake per order
    
    def __str__(self):
        return f"{self.cake.title} - {self.rating} stars by {self.user.username}"
