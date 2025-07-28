# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('pay/<int:order_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
]