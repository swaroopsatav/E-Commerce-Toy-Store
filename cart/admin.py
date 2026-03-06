from django.contrib import admin
from .models import Cart, CartItem
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import redirect

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'added_at')
    list_filter = ('id', 'cart', 'product', 'quantity', 'added_at')
    search_fields = ('id', 'cart', 'product', 'quantity', 'added_at')

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user')
    list_filter = ('id', 'user')
    search_fields = ('id','user')

