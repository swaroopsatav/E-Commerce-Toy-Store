from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from checkout.models import Order, OrderItem, OrderTracking
from checkout.views import payment_method, review_order
from shipping.models import ShippingAddress
from cart.models import Cart, CartItem
from products.models import Product

User = get_user_model()

class PaymentMethodTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('100.00'),
            stock=10
        )
        
        # Create cart and add item
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Create shipping address
        self.address = ShippingAddress.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='1234567890',
            email='test@example.com',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            pincode='123456',
            is_valid_for_cod=True
        )

    def test_payment_method_get(self):
        """Test GET request for payment method selection"""
        response = self.client.get(
            reverse('checkout:payment_method', args=[self.address.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/payment_method.html')
        self.assertIn('address', response.context)
        self.assertIn('cart', response.context)
        self.assertIn('payment_methods', response.context)

    def test_payment_method_post_valid_cod(self):
        """Test POST request with valid COD payment"""
        response = self.client.post(
            reverse('checkout:payment_method', args=[self.address.id]),
            {
                'payment_method': 'cash_on_delivery'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/checkout/review/1/')  # Assuming order ID is 1
        
        order = Order.objects.first()
        self.assertEqual(order.payment_method, 'cash_on_delivery')
        self.assertEqual(order.status, 'pending')

    def test_payment_method_post_invalid_cod(self):
        """Test POST request with invalid COD payment"""
        # Create address not valid for COD
        invalid_address = ShippingAddress.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='1234567890',
            email='test@example.com',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            pincode='123456',
            is_valid_for_cod=False
        )
        
        response = self.client.post(
            reverse('checkout:payment_method', args=[invalid_address.id]),
            {
                'payment_method': 'cash_on_delivery'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/checkout/payment/{invalid_address.id}/')
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Cash on Delivery not available in this area', str(messages[0]))

    def test_payment_method_post_invalid_payment_method(self):
        """Test POST request with invalid payment method"""
        response = self.client.post(
            reverse('checkout:payment_method', args=[self.address.id]),
            {
                'payment_method': 'invalid_method'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/checkout/payment/{self.address.id}/')
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Invalid payment method', str(messages[0]))

    def test_payment_method_post_invalid_address(self):
        """Test POST request with invalid address"""
        response = self.client.post(
            reverse('checkout:payment_method', args=[9999]),  # Non-existent address ID
            {
                'payment_method': 'cash_on_delivery'
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_review_order_get(self):
        """Test GET request for order review"""
        # Create order first
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            payment_method='cash_on_delivery',
            status='pending'
        )
        
        response = self.client.get(
            reverse('checkout:review_order', args=[order.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/review.html')
        self.assertIn('order', response.context)

    @patch('checkout.views.send_order_confirmation_email')
    def test_review_order_post_success(self, mock_send_email):
        """Test successful order processing"""
        # Create order first
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            payment_method='cash_on_delivery',
            status='pending'
        )
        
        response = self.client.post(
            reverse('checkout:review_order', args=[order.id])
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/checkout/success/')
        
        # Refresh order from database
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.status, 'processing')
        
        # Check tracking update was created
        tracking = OrderTracking.objects.filter(order=order).first()
        self.assertIsNotNone(tracking)
        self.assertEqual(tracking.status, 'processing')
        
        # Check order items status was updated
        for item in order.order_items.all():
            self.assertEqual(item.status, 'processing')

    def test_review_order_post_failure(self):
        """Test order processing failure"""
        # Create order first
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            payment_method='cash_on_delivery',
            status='pending'
        )
        
        with patch('checkout.views.transaction.atomic', side_effect=Exception('Payment failed')):
            response = self.client.post(
                reverse('checkout:review_order', args=[order.id])
            )
            
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, f'/checkout/review/{order.id}/')
            messages = list(get_messages(response.wsgi_request))
            self.assertIn('Error processing order', str(messages[0]))

    def test_review_order_nonexistent_order(self):
        """Test accessing review page with non-existent order"""
        response = self.client.get(reverse('checkout:review_order', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_review_order_unauthorized_access(self):
        """Test unauthorized access to review page"""
        # Create order with different user
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        order = Order.objects.create(
            user=other_user,
            shipping_address=self.address,
            cart=self.cart,
            payment_method='cash_on_delivery',
            status='pending'
        )
        
        response = self.client.get(reverse('checkout:review_order', args=[order.id]))
        self.assertEqual(response.status_code, 404)  # Should not find the order
