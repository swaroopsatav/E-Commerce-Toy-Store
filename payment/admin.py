from django.contrib import admin
from .models import Payment
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import Order


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order', 'payment_method', 'status', 'transaction_id')
    list_filter = ('id', 'user', 'order', 'payment_method', 'status', 'transaction_id')
    search_fields = ('id', 'user', 'order', 'payment_method', 'status', 'transaction_id')
