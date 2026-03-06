from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from .forms import OrderForm, OrderItemForm
from .models import Order, OrderItem
from products.models import Product
from users.models import CustomUser

class OrderFormTest(TestCase):
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
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('200.00'),
            status='Pending',
            payment_status='Pending',
            address='123 Test Street'
        )

    def test_valid_order_form(self):
        form_data = {
            'user': self.user.id,
            'total_amount': Decimal('200.00'),
            'status': 'Pending',
            'payment_status': 'Pending',
            'address': '123 Test Street'
        }
        form = OrderForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_order_form(self):
        # Missing required fields
        form_data = {
            'status': 'Pending',
            'payment_status': 'Pending'
        }
        form = OrderForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
        self.assertIn('total_amount', form.errors)
        self.assertIn('address', form.errors)

        # Invalid status
        form_data = {
            'user': self.user.id,
            'total_amount': Decimal('200.00'),
            'status': 'InvalidStatus',
            'payment_status': 'Pending',
            'address': '123 Test Street'
        }
        form = OrderForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)

        # Invalid payment status
        form_data = {
            'user': self.user.id,
            'total_amount': Decimal('200.00'),
            'status': 'Pending',
            'payment_status': 'InvalidStatus',
            'address': '123 Test Street'
        }
        form = OrderForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_status', form.errors)

    def test_order_form_clean(self):
        # Test negative total amount
        form_data = {
            'user': self.user.id,
            'total_amount': Decimal('-200.00'),
            'status': 'Pending',
            'payment_status': 'Pending',
            'address': '123 Test Street'
        }
        form = OrderForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_amount', form.errors)

class OrderItemFormTest(TestCase):
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
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('200.00'),
            status='Pending',
            payment_status='Pending',
            address='123 Test Street'
        )

    def test_valid_order_item_form(self):
        form_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 2,
            'price': Decimal('100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_order_item_form(self):
        # Missing required fields
        form_data = {
            'quantity': 2,
            'price': Decimal('100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('order', form.errors)
        self.assertIn('product', form.errors)

        # Invalid quantity
        form_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 0,
            'price': Decimal('100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

        # Quantity greater than stock
        form_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 11,
            'price': Decimal('100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

        # Invalid price
        form_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 2,
            'price': Decimal('-100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_order_item_form_clean(self):
        # Test valid update
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00')
        )
        form_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 3,
            'price': Decimal('100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Test invalid update (exceeding stock)
        form_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 9,
            'price': Decimal('100.00')
        }
        form = OrderItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)
