from django import forms
from .models import Order, OrderItem

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['user', 'total_amount', 'payment_status', 'status', 'address']
        widgets = {
            'user': forms.HiddenInput(),  # Usually set from request.user
            'status': forms.Select(choices=Order.STATUS_CHOICES),
            'payment_status': forms.Select(choices=[('Pending', 'Pending'), ('Paid', 'Paid')]),
            'total_amount': forms.NumberInput(attrs={'readonly': 'readonly'}),
        }

    def clean_total_amount(self):
        total_amount = self.cleaned_data.get('total_amount')
        if not total_amount:
            raise forms.ValidationError('Total amount is required.')
        return total_amount

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'quantity', 'price']
        widgets = {
            'order': forms.HiddenInput(),
            'price': forms.NumberInput(attrs={'readonly': 'readonly'}),  # Price should not be manually editable
        }
