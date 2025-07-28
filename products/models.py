# products/models.py
from django.db import models
from accounts.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Cake(models.Model):
    DIETARY_CHOICES = [
        ('veg', 'Vegetarian'),
        ('non_veg', 'Non-Vegetarian'),
        ('vegan', 'Vegan'),
        ('eggless', 'Eggless'),
    ]
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'seller'})
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.CharField(max_length=500, help_text="Comma-separated tags")
    flavor = models.CharField(max_length=100)
    dietary = models.CharField(max_length=10, choices=DIETARY_CHOICES)
    is_todays_special = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_main_image(self):
        return self.images.filter(is_main=True).first()

class CakeVariant(models.Model):
    WEIGHT_CHOICES = [
        ('0.5', '0.5 kg'),
        ('1', '1 kg'),
        ('2', '2 kg'),
    ]
    
    cake = models.ForeignKey(Cake, on_delete=models.CASCADE, related_name='variants')
    weight = models.CharField(max_length=5, choices=WEIGHT_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField()
    
    class Meta:
        unique_together = ['cake', 'weight']
    
    def __str__(self):
        return f"{self.cake.title} - {self.weight}kg"
    
    @property
    def is_in_stock(self):
        return self.stock > 0

class CakeImage(models.Model):
    cake = models.ForeignKey(Cake, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.is_main:
            # Ensure only one main image per cake
            CakeImage.objects.filter(cake=self.cake, is_main=True).update(is_main=False)
        super().save(*args, **kwargs)
