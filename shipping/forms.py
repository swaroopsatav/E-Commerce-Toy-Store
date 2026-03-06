from django import forms
from .models import ShippingAddress

class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['order','address','city','state','postal_code','country','phone_number']


    def save(self, commit=True):
        address = super().save(commit=False)
        if commit:
            address.save()
        return address


