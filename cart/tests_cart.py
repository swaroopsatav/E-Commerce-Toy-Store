import os
import uuid
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from django.urls import reverse

from users.models import CustomUser
from products.models import Product, Category
from .models import Cart, CartItem
from .views import cart_home, cart_detail, add_to_cart, remove_from_cart, cart_mini, cart_empty, cart_update, get_cart

class CartModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            is_featured=True
        )
        self.product.categories.add(self.category)
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_creation(self):
        self.assertEqual(self.cart.user, self.user)
        self.assertTrue(self.cart.is_active)
        self.assertEqual(self.cart.total_price, Decimal('0.00'))
        self.assertEqual(self.cart.shipping_amount, Decimal('50.00'))
        self.assertEqual(self.cart.tax_amount, Decimal('0.00'))
        self.assertEqual(self.cart.total_amount, Decimal('50.00'))

    def test_cart_add_item(self):
        with self.assertRaises(ValueError):
            self.cart.add_item(self.product, quantity=0)

        with self.assertRaises(ValueError):
            self.cart.add_item(self.product, quantity=11)  # More than stock

        cart_item = self.cart.add_item(self.product, quantity=5)
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(cart_item.price, self.product.price)
        self.assertEqual(self.cart.calculate_total_price(), Decimal('550.00'))  # 500 + 50 shipping + 50 tax

    def test_cart_remove_item(self):
        self.cart.add_item(self.product, quantity=2)
        self.cart.remove_item(self.product)
        self.assertEqual(self.cart.cart_items.count(), 0)
        self.assertEqual(self.cart.calculate_total_price(), Decimal('50.00'))  # Only shipping

    def test_cart_clear(self):
        self.cart.add_item(self.product, quantity=2)
        self.cart.clear()
        self.assertEqual(self.cart.cart_items.count(), 0)
        self.assertEqual(self.cart.total_price, Decimal('0.00'))
        self.assertEqual(self.cart.shipping_amount, Decimal('50.00'))
        self.assertEqual(self.cart.tax_amount, Decimal('0.00'))
        self.assertEqual(self.cart.total_amount, Decimal('50.00'))

    def test_cart_calculate_total_price(self):
        self.cart.add_item(self.product, quantity=2)
        total = self.cart.calculate_total_price()
        self.assertEqual(total, Decimal('268.00'))  # 200 + 50 shipping + 18 tax

    def test_cart_item_creation(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.total_price(), Decimal('200.00'))

    def test_cart_item_update_quantity(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        cart_item.update_quantity(3)
        self.assertEqual(cart_item.quantity, 3)
        self.assertEqual(cart_item.total_price(), Decimal('300.00'))

    def test_cart_item_clean(self):
        cart_item = CartItem(cart=self.cart, product=self.product, quantity=0)
        with self.assertRaises(ValidationError):
            cart_item.clean()

        cart_item.quantity = 11  # More than stock
        with self.assertRaises(ValidationError):
            cart_item.clean()

class CartViewsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            is_featured=True
        )
        self.product.categories.add(self.category)

    def add_messages_middleware(self, request):
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request

    def test_cart_home_view(self):
        request = self.factory.get(reverse('cart:cart_home'))
        request.user = self.user
        response = cart_home(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/home.html')

    def test_cart_detail_view(self):
        request = self.factory.get(reverse('cart:cart_detail'))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = cart_detail(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_detail.html')

    def test_add_to_cart_view(self):
        request = self.factory.get(reverse('cart:add_to_cart', args=[self.product.id]))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = add_to_cart(request, self.product.id)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())

    def test_remove_from_cart_view(self):
        cart = get_cart(self.user)
        cart.add_item(self.product, quantity=2)
        
        request = self.factory.get(reverse('cart:remove_from_cart', args=[self.product.id]))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = remove_from_cart(request, self.product.id)
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())

    def test_cart_mini_view(self):
        request = self.factory.get(reverse('cart:cart_mini'))
        request.user = self.user
        response = cart_mini(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_mini.html')

    def test_cart_empty_view(self):
        request = self.factory.get(reverse('cart:cart_empty'))
        request.user = self.user
        response = cart_empty(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_empty.html')

    def test_cart_update_view(self):
        request = self.factory.post(reverse('cart:cart_update'), {
            'product_id': self.product.id,
            'quantity': 3
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = cart_update(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CartItem.objects.filter(
            cart__user=self.user,
            product=self.product,
            quantity=3
        ).exists())

    def test_get_cart_function(self):
        cart = get_cart(self.user)
        self.assertEqual(cart.user, self.user)
        self.assertTrue(cart.is_active)

    def test_cart_view(self):
        request = self.factory.get(reverse('cart:cart_view'))
        request.user = self.user
        response = cart_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_view.html')

    def test_cart_view_with_items(self):
        cart = get_cart(self.user)
        cart.add_item(self.product, quantity=2)
        
        request = self.factory.get(reverse('cart:cart_view'))
        request.user = self.user
        response = cart_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_view.html')
        self.assertIn('cart', response.context)
        self.assertIn('cart_items', response.context)
        self.assertIn('total_price', response.context)
        self.assertIn('shipping', response.context)
        self.assertIn('tax', response.context)
        self.assertIn('grand_total', response.context)

    def test_cart_view_empty_cart(self):
        request = self.factory.get(reverse('cart:cart_view'))
        request.user = self.user
        response = cart_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_view.html')
        self.assertIn('cart', response.context)
        self.assertIn('cart_items', response.context)
        self.assertEqual(len(response.context['cart_items']), 0)

    def test_cart_detail_view_with_update(self):
        cart = get_cart(self.user)
        cart.add_item(self.product, quantity=2)
        
        request = self.factory.post(reverse('cart:cart_detail'), {
            'product_id': self.product.id,
            'quantity': 3,
            'cart_update': 'Update'
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = cart_detail(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_detail.html')
        self.assertEqual(CartItem.objects.get(cart__user=self.user, product=self.product).quantity, 3)

    def test_cart_detail_view_with_remove(self):
        cart = get_cart(self.user)
        cart.add_item(self.product, quantity=2)
        
        request = self.factory.post(reverse('cart:cart_detail'), {
            'product_id': self.product.id,
            'remove_from_cart': 'Remove'
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = cart_detail(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart_detail.html')
        self.assertFalse(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())
