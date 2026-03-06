import os
import uuid
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from users.models import CustomUser
from products.models import Product, Category
from .models import Order, OrderItem
from cart.models import Cart, CartItem

class OrderModelTest(TestCase):
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
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('200.00'),
            status='Pending',
            payment_status='Pending',
            address='123 Test Street'
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00')
        )

    def test_order_creation(self):
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.total_amount, Decimal('200.00'))
        self.assertEqual(self.order.status, 'Pending')
        self.assertEqual(self.order.payment_status, 'Pending')
        self.assertTrue(self.order.is_active)
        self.assertIsNotNone(self.order.created_at)
        self.assertIsNotNone(self.order.updated_at)
        self.assertEqual(self.order.address, '123 Test Street')

    def test_order_str_method(self):
        self.assertEqual(str(self.order), f"Order {self.order.id} by {self.user.username}")

    def test_order_item_creation(self):
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product, self.product)
        self.assertEqual(self.order_item.quantity, 2)
        self.assertEqual(self.order_item.price, Decimal('100.00'))

    def test_order_item_str_method(self):
        self.assertEqual(str(self.order_item), f"{self.product.name} x {self.order_item.quantity}")

    def test_order_item_total_price(self):
        self.assertEqual(self.order_item.total_price(), Decimal('200.00'))

    def test_order_item_clean(self):
        # Test invalid quantity
        with self.assertRaises(ValidationError):
            self.order_item.quantity = 0
            self.order_item.clean()

        # Test invalid price
        with self.assertRaises(ValidationError):
            self.order_item.price = Decimal('-100.00')
            self.order_item.clean()

    def test_order_status_validation(self):
        # Test invalid status
        with self.assertRaises(ValidationError):
            self.order.status = 'InvalidStatus'
            self.order.full_clean()

    def test_order_payment_status_validation(self):
        # Test invalid payment status
        with self.assertRaises(ValidationError):
            self.order.payment_status = 'InvalidStatus'
            self.order.full_clean()

    def test_order_total_amount_calculation(self):
        # Add another item to test total calculation
        second_product = Product.objects.create(
            name='Second Product',
            description='Second product description',
            price=Decimal('150.00'),
            stock=5,
            is_active=True,
            is_featured=True
        )
        second_product.categories.add(self.category)
        OrderItem.objects.create(
            order=self.order,
            product=second_product,
            quantity=1,
            price=Decimal('150.00')
        )
        self.assertEqual(self.order.total_amount, Decimal('350.00'))

    def test_order_cancel(self):
        self.order.cancel()
        self.assertEqual(self.order.status, 'Cancelled')
        self.assertEqual(self.order.payment_status, 'Cancelled')

    def test_order_deliver(self):
        self.order.deliver()
        self.assertEqual(self.order.status, 'Delivered')
        self.assertEqual(self.order.payment_status, 'Paid')
