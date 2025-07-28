# reviews/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Example URLs - adjust according to your views
    path('add/<int:order_id>/<int:cake_id>/', views.add_review, name='add_review'),
    path('cake/<int:cake_id>/', views.cake_reviews, name='cake_reviews'),
]
