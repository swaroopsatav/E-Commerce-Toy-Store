from django.urls import path

from . import views

app_name = 'payment'

urlpatterns = [
    path("", views.payment_home, name="payment_home"),
    path('payment_page/', views.payment_page, name='payment_page'),
    path('payment_processing/', views.process_payment, name='process_payment'),
    path('payment_confirmation/<uuid:payment_id>/', views.payment_confirmation, name='payment_confirmation'),
    path('payment_history/', views.payment_history, name='payment_history'),
    ]
