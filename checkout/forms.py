from django import forms
from orders.models import Order
from shipping.models import ShippingAddress
from payment.models import Payment

class CheckoutForm(forms.ModelForm):
    shipping_address = forms.ModelChoiceField(
        queryset=ShippingAddress.objects.all(),
        empty_label="Select a shipping address",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    payment_method = forms.ChoiceField(
        choices=[('credit_card', 'Credit Card'), ('paypal', 'PayPal')],
        widget=forms.RadioSelect()
    )

    class Meta:
        model = Order
        fields = ['shipping_address', 'payment_method']
