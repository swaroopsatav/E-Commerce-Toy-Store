import os
import uuid
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from users.models import CustomUser
from products.models import Product, Category
from cart.models import Cart, CartItem
from .models import ShippingAddress, Order, OrderItem, OrderTracking, OrderCancellation

class ShippingAddressModelTest(TestCase):
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

    def test_shipping_address_creation(self):
        self.assertEqual(self.address.user, self.user)
        self.assertEqual(self.address.full_name, 'John Doe')
        self.assertEqual(self.address.phone_number, '1234567890')
        self.assertTrue(self.address.is_validated)
        self.assertIsNotNone(self.address.created_at)
        self.assertIsNotNone(self.address.updated_at)

    def test_address_validation(self):
        # Test invalid phone number
        self.address.phone_number = '123'
        with self.assertRaises(ValidationError):
            self.address.validate_address()

        # Test invalid pincode
        self.address.phone_number = '1234567890'
        self.address.pincode = '123'
        with self.assertRaises(ValidationError):
            self.address.validate_address()

        # Test missing city
        self.address.pincode = '10001'
        self.address.city = ''
        with self.assertRaises(ValidationError):
            self.address.validate_address()

    def test_default_address(self):
        # Create another address
        second_address = ShippingAddress.objects.create(
            user=self.user,
            full_name='Jane Doe',
            phone_number='0987654321',
            email='jane@example.com',
            address_line1='456 Main St',
            city='New York',
            state='NY',
            pincode='10002',
            country='USA'
        )
        
        # Make second address default
        second_address.is_default = True
        second_address.save()
        
        # First address should no longer be default
        self.address.refresh_from_db()
        self.assertFalse(self.address.is_default)

    def test_address_string_representation(self):
        self.assertEqual(str(self.address), f"{self.address.full_name} - {self.address.address_line1}")

class OrderModelTest(TestCase):
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
        self.order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            order_number='ORD123456',
            payment_method='cash_on_delivery'
        )
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            is_featured=True
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00')
        )

    def test_order_creation(self):
        """Test order creation with all required fields"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.shipping_address, self.address)
        self.assertEqual(self.order.payment_method, 'cash_on_delivery')
        self.assertEqual(self.order.status, 'pending')
        self.assertIsNotNone(self.order.created_at)
        self.assertIsNotNone(self.order.updated_at)
        self.assertIsNotNone(self.order.order_number)
        self.assertEqual(self.order.total_amount, Decimal('0.00'))  # Initial total is 0

    def test_order_total_calculation(self):
        """Test order total calculation with shipping and tax"""
        # Test total calculation
        self.order.calculate_total()
        self.assertEqual(self.order.total_amount, Decimal('221.00'))  # 200 + 20 shipping + 21 tax
        self.assertEqual(self.order.shipping_amount, Decimal('20.00'))
        self.assertEqual(self.order.tax_amount, Decimal('21.00'))

    def test_order_status_updates(self):
        """Test order status updates with proper validation"""
        # Test valid status transition
        self.order.update_status('confirmed')
        self.assertEqual(self.order.status, 'confirmed')
        
        # Test invalid status transition
        with self.assertRaises(ValidationError):
            self.order.update_status('delivered')

    def test_payment_status_updates(self):
        """Test payment status updates"""
        # Test payment status update
        self.order.payment_status = 'paid'
        self.order.save()
        self.assertEqual(self.order.payment_status, 'paid')
        
        # Test invalid payment status
        with self.assertRaises(ValidationError):
            self.order.payment_status = 'invalid'
            self.order.save()

    def test_cod_eligibility(self):
        """Test COD eligibility validation"""
        # Test valid COD order
        self.assertTrue(self.order.is_cod_eligible())
        
        # Test invalid COD order (address not valid for COD)
        self.address.is_valid_for_cod = False
        self.address.save()
        self.assertFalse(self.order.is_cod_eligible())

    def test_stock_update(self):
        """Test product stock update after order"""
        initial_stock = self.product.stock
        
        # Test stock update for confirmed order
        self.order.status = 'confirmed'
        self.order.save()
        self.order.update_stock()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 2)
        
        # Test stock update for cancelled order
        self.order.status = 'cancelled'
        self.order.save()
        self.order.update_stock()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

    def test_order_tracking(self):
        """Test order tracking updates"""
        # Create tracking update
        tracking = OrderTracking.objects.create(
            order=self.order,
            status='confirmed',
            notes='Order confirmed'
        )
        
        self.assertEqual(self.order.tracking_updates.count(), 1)
        self.assertEqual(tracking.status, 'confirmed')
        self.assertEqual(tracking.notes, 'Order confirmed')

    def test_order_cancellation(self):
        """Test order cancellation"""
        # Create cancellation request
        cancellation = OrderCancellation.objects.create(
            order=self.order,
            reason='Changed my mind'
        )
        
        self.assertEqual(self.order.cancellation_requests.count(), 1)
        self.assertEqual(cancellation.reason, 'Changed my mind')
        
        # Test cancellation status update
        self.order.status = 'cancelled'
        self.order.save()
        self.assertEqual(self.order.status, 'cancelled')

    def test_order_string_representation(self):
        """Test order string representation"""
        self.assertEqual(str(self.order), f'Order #{self.order.order_number} - {self.user.username}')

    def test_order_validation(self):
        """Test order validation rules"""
        # Test invalid payment method
        self.order.payment_method = 'invalid_method'
        with self.assertRaises(ValidationError):
            self.order.full_clean()
            
        # Test invalid status
        self.order.payment_method = 'cash_on_delivery'
        self.order.status = 'invalid_status'
        with self.assertRaises(ValidationError):
            self.order.full_clean()
            
        # Test invalid shipping address
        self.order.status = 'pending'
        self.order.shipping_address = None
        with self.assertRaises(ValidationError):
            self.order.full_clean()

class OrderItemModelTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test category and product
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            price=Decimal('100.00'),
            stock=10
        )
        
        # Create test cart and cart item
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Create test shipping address
        self.address = ShippingAddress.objects.create(
            user=self.user,
            full_name='John Doe',
            phone_number='1234567890',
            email='john@example.com',
            address_line1='123 Main St',
            city='New York',
            state='NY',
            pincode='10001',
            country='USA',
            is_valid_for_cod=True
        )
        
        # Create test order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            payment_method='cash_on_delivery',
            status='pending'
        )
        
        # Create test order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00')
        )

    def test_order_item_creation(self):
        """Test order item creation with all required fields"""
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product, self.product)
        self.assertEqual(self.order_item.quantity, 2)
        self.assertEqual(self.order_item.price, Decimal('100.00'))
        self.assertIsNotNone(self.order_item.created_at)
        self.assertIsNotNone(self.order_item.updated_at)

    def test_order_item_status_updates(self):
        """Test order item status updates with proper validation"""
        # Test valid status transition
        self.order_item.update_status('processing')
        self.assertEqual(self.order_item.status, 'processing')
        
        # Test invalid status transition
        with self.assertRaises(ValidationError):
            self.order_item.update_status('delivered')

    def test_order_item_tracking(self):
        """Test order item tracking updates"""
        # Create tracking update
        tracking = OrderTracking.objects.create(
            order=self.order,
            status='processing',
            notes='Item processing started'
        )
        
        self.assertEqual(self.order.tracking_updates.count(), 1)
        self.assertEqual(tracking.status, 'processing')
        self.assertEqual(tracking.notes, 'Item processing started')

    def test_order_item_stock_update(self):
        """Test product stock update for order item"""
        initial_stock = self.product.stock
        
        # Test stock update for confirmed order item
        self.order_item.status = 'confirmed'
        self.order_item.save()
        self.order_item.update_stock()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock - 2)
        
        # Test stock update for cancelled order item
        self.order_item.status = 'cancelled'
        self.order_item.save()
        self.order_item.update_stock()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

    def test_order_item_price_validation(self):
        """Test order item price validation"""
        # Test price validation
        self.order_item.price = Decimal('0.00')
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()
            
        self.order_item.price = Decimal('-100.00')
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()

    def test_order_item_quantity_validation(self):
        """Test order item quantity validation"""
        # Test quantity validation
        self.order_item.quantity = 0
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()
            
        self.order_item.quantity = -1
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()

    def test_order_item_string_representation(self):
        """Test order item string representation"""
        self.assertEqual(str(self.order_item), f'{self.product.name} x {self.order_item.quantity}')

    def test_order_item_validation(self):
        """Test order item validation rules"""
        # Test invalid order
        self.order_item.order = None
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()
            
        # Test invalid product
        self.order_item.order = self.order
        self.order_item.product = None
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()
            
        # Test invalid quantity
        self.order_item.product = self.product
        self.order_item.quantity = 0
        with self.assertRaises(ValidationError):
            self.order_item.full_clean()

    def test_payment_status_updates(self):
        """Test payment status updates"""
        # Test payment status update
        self.order_item.payment_status = 'paid'
        self.order_item.save()
        self.assertEqual(self.order_item.payment_status, 'paid')
        
        # Test invalid payment status
        with self.assertRaises(ValidationError):
            self.order_item.payment_status = 'invalid'
            self.order_item.save()

    def test_payment_method_updates(self):
        """Test payment method updates"""
        # Test payment method update
        self.order_item.payment_method = 'online_payment'
        self.order_item.save()
        self.assertEqual(self.order_item.payment_method, 'online_payment')
        
        # Test invalid payment method
        with self.assertRaises(ValidationError):
            self.order_item.payment_method = 'invalid_method'
            self.order_item.save()

class OrderCancellationModelTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test category and product
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            price=Decimal('100.00'),
            stock=10
        )
        
        # Create test cart and cart item
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Create test shipping address
        self.address = ShippingAddress.objects.create(
            user=self.user,
            full_name='John Doe',
            phone_number='1234567890',
            email='john@example.com',
            address_line1='123 Main St',
            city='New York',
            state='NY',
            pincode='10001',
            country='USA',
            is_valid_for_cod=True
        )
        
        # Create test order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            payment_method='cash_on_delivery',
            status='pending'
        )
        
        # Create test order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00')
        )
        
        # Create test cancellation
        self.cancellation = OrderCancellation.objects.create(
            order=self.order,
            reason='Changed my mind'
        )

    def test_order_cancellation_creation(self):
        """Test order cancellation creation with all required fields"""
        self.assertEqual(self.cancellation.order, self.order)
        self.assertEqual(self.cancellation.reason, 'Changed my mind')
        self.assertIsNotNone(self.cancellation.created_at)
        self.assertIsNotNone(self.cancellation.updated_at)

    def test_cancellation_status_updates(self):
        """Test cancellation status updates with proper validation"""
        # Test valid status transition
        self.cancellation.update_status('approved')
        self.assertEqual(self.cancellation.status, 'approved')
        
        # Test invalid status transition
        with self.assertRaises(ValidationError):
            self.cancellation.update_status('invalid_status')

    def test_cancellation_refund_processing(self):
        """Test refund processing for cancelled order"""
        # Set order as paid
        self.order.payment_status = 'paid'
        self.order.save()
        
        # Approve cancellation
        self.cancellation.update_status('approved')
        
        # Test refund processing
        refund = self.cancellation.process_refund()
        self.assertIsNotNone(refund)
        self.assertEqual(refund.amount, self.order.total_amount)
        self.assertEqual(refund.status, 'processed')
        
        # Test stock restoration
        initial_stock = self.product.stock
        self.cancellation.restore_stock()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock + 2)

    def test_cancellation_string_representation(self):
        """Test cancellation string representation"""
        self.assertEqual(str(self.cancellation), f'Cancellation #{self.cancellation.id} - {self.order.order_number}')

    def test_cancellation_validation(self):
        """Test cancellation validation rules"""
        # Test invalid order
        self.cancellation.order = None
        with self.assertRaises(ValidationError):
            self.cancellation.full_clean()
            
        # Test invalid reason
        self.cancellation.order = self.order
        self.cancellation.reason = ''
        with self.assertRaises(ValidationError):
            self.cancellation.full_clean()
            
        # Test invalid status
        self.cancellation.reason = 'Changed my mind'
        self.cancellation.status = 'invalid_status'
        with self.assertRaises(ValidationError):
            self.cancellation.full_clean()
