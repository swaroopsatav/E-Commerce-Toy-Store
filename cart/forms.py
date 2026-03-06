from django import forms
from .models import Cart, CartItem

class CartForm(forms.ModelForm):
    class Meta:
        model = Cart
        fields = ['user','is_active','created_at']

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['cart','user','product','quantity','price','added_at']
