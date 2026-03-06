from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from users.models import CustomUser
from products.models import Product, Category
from cart.models import Cart, CartItem
from shipping.models import ShippingAddress
from .forms import CheckoutForm

class CheckoutFormTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.address = ShippingAddress.objects.create(
            user=self.user,
            full_name='John Doe',
            phone_number='1234567890',
            email='john@example.com',
            address_line1='123 Main St',
            city='New York',
            state='NY',
            pincode='10001',
            country='USA'
        )
        self.cart = Cart.objects.create(user=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            is_featured=True
        )
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price=self.product.price
        )

    def test_valid_checkout_form(self):
        form_data = {
            'shipping_address': self.address.id,
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_checkout_form(self):
        # Missing shipping address
        form_data = {
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shipping_address', form.errors)

        # Invalid payment method
        form_data = {
            'shipping_address': self.address.id,
            'payment_method': 'invalid_method'
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)

    def test_empty_shipping_address(self):
        # No shipping addresses available
        self.address.delete()
        form_data = {
            'shipping_address': '',
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shipping_address', form.errors)

    def test_invalid_shipping_address(self):
        # Invalid shipping address ID
        form_data = {
            'shipping_address': 9999,
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shipping_address', form.errors)

    def test_form_clean(self):
        # Test clean method with valid data
        form_data = {
            'shipping_address': self.address.id,
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Test clean method with invalid shipping address
        self.address.delete()
        form_data = {
            'shipping_address': self.address.id,
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shipping_address', form.errors)

    def test_form_save(self):
        form_data = {
            'shipping_address': self.address.id,
            'payment_method': 'credit_card'
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test save method
        order = form.save(commit=False)
        order.user = self.user
        order.cart = self.cart
        order.save()
        
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.shipping_address, self.address)
        self.assertEqual(order.payment_method, 'credit_card')
        self.assertIsNotNone(order.created_at)
        self.assertIsNotNone(order.updated_at)
