from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path("", views.cart_home, name="cart"),
    path('cart_view/', views.cart_view, name='cart_view'),
    path('cart_detail/', views.cart_detail, name='cart_detail'),
    path('add_to_cart/<uuid:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<uuid:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart_mini/', views.cart_mini, name='cart_mini'),
    path('cart_empty/', views.cart_empty, name='cart_empty'),
    path('cart_update/<uuid:cart_id>/', views.cart_update, name='cart_update'),
    ]

