from django.urls import path

from . import views

app_name = 'checkout'

urlpatterns = [
    path('start/', views.start_checkout, name='start_checkout'),
    path('shipping_address/', views.shipping_address, name='shipping_address'),
    path('payment_method/<int:address_id>/', views.payment_method, name='payment_method'),
    path('review_order/<int:address_id>/<str:payment_method>/', views.review_order, name='review_order'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('update_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('get_tracking/<int:order_id>/', views.get_order_tracking, name='get_order_tracking'),
    path('cancel_order/<int:order_id>/', views.request_order_cancellation, name='request_order_cancellation'),
    path('tracking/<int:order_id>/', views.order_tracking, name='order_tracking'),
]
