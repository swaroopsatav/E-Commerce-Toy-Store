from django.urls import path

from . import views

app_name = 'shipping'

urlpatterns = [
    path("", views.shipping_home, name="shipping_home"),
    path('address_list/', views.list_addresses, name='list_addresses'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/edit/<uuid:address_id>/', views.update_address, name='update_address'),
    path('address/delete/<uuid:address_id>/', views.delete_address, name='delete_address'),

    ]

