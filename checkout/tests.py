from decimal import Decimal
import random
import datetime
import csv
import io
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from products.models import Category
from users.models import CustomUser
from unittest.mock import patch
from products.models import Product
from cart.models import Cart, CartItem
from shipping.models import ShippingAddress
from .views import checkout_view
from orders.models import Order,OrderItem
import uuid
from orders.models import Order
from shipping.models import ShippingAddress
from payment.models import Payment
from checkout.forms import CheckoutForm


class CheckoutFormTest(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(username="testuser", password="password123")

        self.shipping_address = ShippingAddress.objects.create(
            user=self.user,  # Assign the test user
            address="123 Test St",
            city="Test City",
            postal_code="12345"
        )

        self.order = Order.objects.create(user=self.user)

    def test_valid_form(self):
        form_data = {
            'shipping_address': self.shipping_address.id,
            'payment_method': 'credit_card',
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_shipping_address(self):
        form_data = {
            'payment_method': 'paypal',
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('shipping_address', form.errors)

    def test_invalid_form_missing_payment_method(self):
        form_data = {
            'shipping_address': self.shipping_address.id,
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)


class CheckoutViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Create test products
        self.product1 = Product.objects.create(name='Test Product 1', price=Decimal('100.00'))
        self.product2 = Product.objects.create(name='Test Product 2', price=Decimal('50.00'))

        # Add items to cart
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item1 = CartItem.objects.create(cart=self.cart, product=self.product1, quantity=2)
        self.cart_item2 = CartItem.objects.create(cart=self.cart, product=self.product2, quantity=1)

        # Create shipping address
        self.shipping_address = ShippingAddress.objects.create(
            user=self.user, 
            address='123 Street', 
            city='Test City', 
            state='TS', 
            postal_code='12345'
        )
        
        # Create order
        self.order = Order.objects.create(
            id=uuid.uuid4(), 
            user=self.user,
            total_amount=Decimal('250.00'),  # 2 * 100 + 1 * 50
            shipping_address=self.shipping_address
        )

    def test_checkout_view_get(self):
        response = self.client.get(reverse('checkout:checkout_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/checkout_view.html')
        self.assertContains(response, 'Test Product 1')
        self.assertContains(response, 'Test Product 2')
        self.assertContains(response, 'Total: $250.00')

    def test_checkout_view_post_empty_cart(self):
        # Clear cart
        self.cart.cartitem_set.all().delete()
        
        response = self.client.post(reverse('checkout:checkout_view'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart:cart_detail'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Your cart is empty. Please add items before checkout.')

    def test_checkout_view_post_invalid_address(self):
        response = self.client.post(reverse('checkout:checkout_view'), {
            'address': '',  # Empty address
            'city': 'New City',
            'state': 'NS',
            'postal_code': '67890'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'address', 'This field is required.')

    def test_checkout_payment_get(self):
        response = self.client.get(reverse('checkout:checkout_payment'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/checkout_payment.html')
        self.assertContains(response, 'Total: $250.00')

    def test_checkout_payment_post_invalid_method(self):
        response = self.client.post(reverse('checkout:checkout_payment'), {
            'payment_method': 'invalid_method'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'payment_method', 'Select a valid choice.')

    def test_checkout_payment_post_success(self):
        response = self.client.post(reverse('checkout:checkout_payment'), {
            'payment_method': 'credit_card'
        })
        self.assertRedirects(response, reverse('checkout:checkout_success'))
        self.assertTrue(Order.objects.filter(
            user=self.user, 
            status='Confirmed',
            total_amount=Decimal('250.00')
        ).exists())

    def test_checkout_success(self):
        response = self.client.get(reverse('checkout:checkout_success'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/checkout_success.html')
        self.assertContains(response, 'Order Confirmed')

    def test_checkout_confirmation_get(self):
        response = self.client.get(reverse('checkout:checkout_confirmation'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/checkout_confirmation.html')
        self.assertContains(response, 'Shipping Address')
        self.assertContains(response, 'Payment Method')

    def test_checkout_confirmation_post(self):
        response = self.client.post(reverse('checkout:checkout_confirmation'))
        self.assertRedirects(response, reverse('checkout:checkout_payment'))
        self.assertTrue(Order.objects.filter(
            user=self.user,
            status='Pending'
        ).exists())

    def test_checkout_shipping_get(self):
        response = self.client.get(reverse('checkout:checkout_shipping'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/checkout_shipping.html')
        self.assertContains(response, 'Shipping Address')

    def test_checkout_shipping_post(self):
        response = self.client.post(reverse('checkout:checkout_shipping'), {
            'address': '789 Another St',
            'city': 'Another City',
            'state': 'AC',
            'postal_code': '98765'
        })
        self.assertRedirects(response, reverse('checkout:checkout_review'))
        self.assertTrue(ShippingAddress.objects.filter(
            user=self.user, 
            city='Another City'
        ).exists())

    def test_checkout_review_get(self):
        response = self.client.get(reverse('checkout:checkout_review'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/checkout_review.html')
        self.assertContains(response, 'Order Summary')
        self.assertContains(response, 'Total: $250.00')

    def test_checkout_review_post_invalid(self):
        # Remove shipping address
        self.shipping_address.delete()
        
        response = self.client.post(reverse('checkout:checkout_review'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please select a shipping address')

    def test_checkout_review_post_success(self):
        response = self.client.post(reverse('checkout:checkout_review'), {
            'shipping_address': self.shipping_address.id
        })
        self.assertRedirects(response, reverse('checkout:checkout_payment'))
        self.assertTrue(Order.objects.filter(
            user=self.user,
            shipping_address=self.shipping_address
        ).exists())



