from django import forms
from .models import Payment

class PaymentForm(forms.Form):
    class Meta:
        model = Payment
        fields = ['user','order','payment_method','status','payment_date','transaction_id']
