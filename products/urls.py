# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cakes/', views.cake_list, name='cake_list'),
    path('cakes/<int:cake_id>/', views.cake_detail, name='cake_detail'),
]