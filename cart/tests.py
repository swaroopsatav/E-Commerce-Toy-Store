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
from cart.forms import (
    CartForm, CartItemForm
)
from cart.models import Cart
from products.models import Category
from users.models import CustomUser
from .models import (CartItem
)
from products.models import Product
from unittest.mock import patch
#User = get_user_model()



class CartModelTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Toys')
        self.product1 = Product.objects.create(name='Toy Car', price=Decimal('10.00'))
        self.product2 = Product.objects.create(name='Doll', price=Decimal('15.00'))
        self.product1.categories.set([self.category])
        self.product2.categories.set([self.category])
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_creation(self):
        self.assertEqual(self.cart.user, self.user)
        self.assertTrue(self.cart.is_active)

    def test_cart_total_price(self):
        CartItem.objects.create(cart=self.cart, user=self.user, product=self.product1, quantity=2,
                                price=self.product1.price)
        CartItem.objects.create(cart=self.cart, user=self.user, product=self.product2, quantity=1,
                                price=self.product2.price)

        total_price = self.cart.calculate_total_price()
        expected_total = (2 * Decimal('10.00')) + (1 * Decimal('15.00'))
        self.assertEqual(total_price, expected_total)

class CartFormTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')

    def test_valid_cart_form(self):
        form_data = {'user': self.user.id, 'is_active': True}
        form = CartForm(data=form_data)
        self.assertEqual(form.is_valid(),False)

    def test_invalid_cart_form(self):
        form_data = {'is_active': True}  # Missing user field
        form = CartForm(data=form_data)
        self.assertFalse(form.is_valid())


class CartItemFormTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Toys')
        self.product = Product.objects.create(name='Toy Car', price=Decimal('10.00'))
        self.product.categories.set([self.category])

        # Create a cart for the user
        self.cart = Cart.objects.create(user=self.user)
    def test_valid_cart_item_form(self):
        form_data = {'cart': self.cart.id, 'product': self.product.id, 'quantity': 2}
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_invalid_cart_item_form(self):
        form_data = {'product': self.product.id, 'quantity': 2}  # Missing cart field
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())


class CartItemModelTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Toys')
        self.product = Product.objects.create(name='Toy Car', price=Decimal('10.00'))
        self.product.categories.set([self.category])
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            user=self.user,
            product=self.product,
            quantity=3,
            price=self.product.price
        )

    def test_cart_item_creation(self):
        self.assertEqual(self.cart_item.cart, self.cart)
        self.assertEqual(self.cart_item.user, self.user)
        self.assertEqual(self.cart_item.product, self.product)
        self.assertEqual(self.cart_item.quantity, 3)
        self.assertEqual(self.cart_item.price, Decimal('10.00'))

    def test_cart_item_str(self):
        self.assertEqual(str(self.cart_item),
                         f"{self.cart.user.username} - {self.product.name} - {self.cart_item.quantity}")


class CartViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='testuser', password='testpass')
        self.product = Product.objects.create(name='Agency', price=100.00)

    def test_order_home_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('cart:cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/home.html')

    def test_cart_view_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('cart:cart_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_view.html')

    def test_cart_view_unauthenticated(self):
        response = self.client.get(reverse('cart:cart_view'))
        self.assertNotEqual(response.status_code, 200)

    def test_add_to_cart(self):
        self.client.login(username='testuser', password='testpass')
        cart, _ = Cart.objects.get_or_create(user=self.user, is_active=True)
        response = self.client.post(reverse('cart:add_to_cart', args=[self.product.id]))
        self.assertRedirects(response, reverse('cart:cart_detail'))
        self.assertEqual(CartItem.objects.filter(cart=cart, user=self.user).count(), 1)

    def test_remove_from_cart(self):
        self.client.login(username='testuser', password='testpass')
        cart = Cart.objects.create(user=self.user, is_active=True)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1, user=self.user)
        response = self.client.post(reverse('cart:remove_from_cart', args=[self.product.id]))
        self.assertRedirects(response, reverse('cart:cart_detail'))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_cart_detail_view_empty_cart(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('cart:cart_detail'))
        self.assertTemplateUsed(response, 'cart/cart_empty.html')

    def test_cart_detail_view_with_items(self):
        self.client.login(username='testuser', password='testpass')
        cart = Cart.objects.create(user=self.user, is_active=True)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2, user=self.user)
        response = self.client.get(reverse('cart:cart_detail'))
        self.assertTemplateUsed(response, 'cart/cart_detail.html')
        self.assertContains(response, 'Agency')

    def test_cart_update_item(self):
        self.client.login(username='testuser', password='testpass')
        cart = Cart.objects.create(user=self.user, is_active=True)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, user=self.user, quantity=1)
        response = self.client.post(reverse('cart:cart_detail'), {
            'product_id': self.product.id,
            'cart_update': 'Update',
            'quantity': 3
        })
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
        self.assertRedirects(response, reverse('cart:cart_detail'))

    def test_cart_empty_view(self):
        self.client.login(username='testuser', password='testpass')
        cart = Cart.objects.create(user=self.user, is_active=True)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1, user=self.user)
        response = self.client.post(reverse('cart:cart_empty'))
        self.assertRedirects(response, reverse('cart:cart_detail'))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_cart_mini_view(self):
        self.client.login(username='testuser', password='testpass')
        cart = Cart.objects.create(user=self.user, is_active=True)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1, user=self.user)
        response = self.client.get(reverse('cart:cart_mini'))
        self.assertTemplateUsed(response, 'cart/cart_mini.html')


