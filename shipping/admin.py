from django.contrib import admin
from .models import ShippingAddress

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order', 'city', 'state', 'postal_code', 'country', 'phone_number')
    list_filter = ('id', 'user', 'order', 'city', 'state', 'postal_code', 'country', 'phone_number')
    search_fields = ('id', 'user', 'order', 'city', 'state', 'postal_code', 'country', 'phone_number')
