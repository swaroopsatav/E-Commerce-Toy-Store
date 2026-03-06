from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from .forms import CartForm, CartItemForm
from .models import Cart, CartItem
from products.models import Product
from users.models import CustomUser

class CartFormTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_valid_cart_form(self):
        form_data = {
            'user': self.user.id,
            'is_active': True
        }
        form = CartForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_cart_form(self):
        # Missing user field
        form_data = {
            'is_active': True
        }
        form = CartForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)

    def test_cart_form_clean(self):
        cart = Cart.objects.create(user=self.user)
        form_data = {
            'user': self.user.id,
            'is_active': True
        }
        form = CartForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)

class CartItemFormTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            is_featured=True
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_valid_cart_item_form(self):
        form_data = {
            'cart': self.cart.id,
            'product': self.product.id,
            'quantity': 2
        }
        form = CartItemForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_cart_item_form(self):
        # Missing cart field
        form_data = {
            'product': self.product.id,
            'quantity': 2
        }
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cart', form.errors)

        # Invalid quantity
        form_data = {
            'cart': self.cart.id,
            'product': self.product.id,
            'quantity': 0
        }
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

        # Quantity greater than stock
        form_data = {
            'cart': self.cart.id,
            'product': self.product.id,
            'quantity': 11
        }
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_cart_item_form_clean(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Test adding more items than stock
        form_data = {
            'cart': self.cart.id,
            'product': self.product.id,
            'quantity': 9
        }
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

        # Test valid update
        form_data = {
            'cart': self.cart.id,
            'product': self.product.id,
            'quantity': 3
        }
        form = CartItemForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Test invalid product
        form_data = {
            'cart': self.cart.id,
            'product': 9999,
            'quantity': 2
        }
        form = CartItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('product', form.errors)
