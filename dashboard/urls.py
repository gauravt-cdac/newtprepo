# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('seller-approval/', views.seller_approval, name='seller_approval'),
    path('review-approval/', views.review_approval, name='review_approval'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
]
