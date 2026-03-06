import os
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError

from users.models import CustomUser
from products.models import Product, Category
from cart.models import Cart, CartItem
from shipping.models import ShippingAddress
from .models import Order, OrderItem, OrderTracking, OrderCancellation
from .views import (
    order_tracking, update_order_status, get_order_tracking,
    request_order_cancellation, start_checkout, shipping_address,
    payment_method, review_order, checkout_success, checkout_confirmation,
    checkout_shipping, checkout_review, generate_order_number
)

class CheckoutViewsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
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
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            cart=self.cart,
            order_number='ORD123456'
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00')
        )

    def add_messages_middleware(self, request):
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request

    def test_order_tracking_view(self):
        # Test valid order tracking
        request = self.factory.get(reverse('checkout:order_tracking', args=[self.order.id]))
        request.user = self.user
        response = order_tracking(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/tracking.html')
        
        # Test invalid order
        invalid_order_id = 9999
        request = self.factory.get(reverse('checkout:order_tracking', args=[invalid_order_id]))
        request.user = self.user
        response = order_tracking(request, invalid_order_id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart:cart_detail'))

    def test_update_order_status_view(self):
        # Test valid status update
        request = self.factory.post(reverse('checkout:update_order_status', args=[self.order.id]), {
            'status': 'processing',
            'notes': 'Order processing started'
        })
        request.user = self.user
        response = update_order_status(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'processing')
        
        # Test invalid status
        request = self.factory.post(reverse('checkout:update_order_status', args=[self.order.id]), {
            'status': 'invalid_status',
            'notes': 'Test'
        })
        request.user = self.user
        response = update_order_status(request, self.order.id)
        self.assertEqual(response.status_code, 400)
        
        # Test invalid order
        invalid_order_id = 9999
        request = self.factory.post(reverse('checkout:update_order_status', args=[invalid_order_id]), {
            'status': 'processing',
            'notes': 'Test'
        })
        request.user = self.user
        response = update_order_status(request, invalid_order_id)
        self.assertEqual(response.status_code, 404)

    def test_get_order_tracking_view(self):
        # Test valid tracking
        request = self.factory.get(reverse('checkout:get_order_tracking', args=[self.order.id]))
        request.user = self.user
        response = get_order_tracking(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn('tracking', response.json())
        
        # Test invalid order
        invalid_order_id = 9999
        request = self.factory.get(reverse('checkout:get_order_tracking', args=[invalid_order_id]))
        request.user = self.user
        response = get_order_tracking(request, invalid_order_id)
        self.assertEqual(response.status_code, 404)

    def test_request_order_cancellation_view(self):
        # Test valid cancellation request
        request = self.factory.post(reverse('checkout:request_order_cancellation', args=[self.order.id]), {
            'reason': 'Changed my mind'
        })
        request.user = self.user
        response = request_order_cancellation(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn('cancellation_id', response.json())
        
        # Test invalid order status
        self.order.status = 'delivered'
        self.order.save()
        request = self.factory.post(reverse('checkout:request_order_cancellation', args=[self.order.id]), {
            'reason': 'Changed my mind'
        })
        request.user = self.user
        response = request_order_cancellation(request, self.order.id)
        self.assertEqual(response.status_code, 400)
        
        # Test missing reason
        request = self.factory.post(reverse('checkout:request_order_cancellation', args=[self.order.id]))
        request.user = self.user
        response = request_order_cancellation(request, self.order.id)
        self.assertEqual(response.status_code, 400)

    def test_shipping_address_view(self):
        # Test GET request
        request = self.factory.get(reverse('checkout:shipping_address'))
        request.user = self.user
        response = shipping_address(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/shipping.html')
        
        # Test POST request with valid data
        request = self.factory.post(reverse('checkout:shipping_address'), {
            'full_name': 'Jane Doe',
            'phone_number': '0987654321',
            'email': 'jane@example.com',
            'address_line1': '456 Main St',
            'city': 'New York',
            'state': 'NY',
            'pincode': '10002'
        })
        request.user = self.user
        response = shipping_address(request)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('checkout:checkout_review'))
        
        # Test POST request with invalid data
        request = self.factory.post(reverse('checkout:shipping_address'), {
            'full_name': '',  # Empty required field
            'phone_number': '123',  # Invalid phone number
            'pincode': '123'  # Invalid pincode
        })
        request.user = self.user
        response = shipping_address(request)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'full_name', 'This field is required.')

    def test_payment_method_view(self):
        # Test GET request
        request = self.factory.get(reverse('checkout:payment_method', args=[self.address.id]))
        request.user = self.user
        response = payment_method(request, self.address.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/payment.html')
        
        # Test POST request
        request = self.factory.post(reverse('checkout:payment_method', args=[self.address.id]), {
            'payment_method': 'credit_card'
        })
        request.user = self.user
        response = payment_method(request, self.address.id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('checkout:review_order',
                                             kwargs={'address_id': self.address.id,
                                                    'payment_method': 'credit_card'}))

    def test_review_order_view(self):
        # Test valid review
        request = self.factory.get(reverse('checkout:review_order',
                                         kwargs={'address_id': self.address.id,
                                                'payment_method': 'credit_card'}))
        request.user = self.user
        response = review_order(request, self.address.id, 'credit_card')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/review.html')
        
        # Test invalid address
        invalid_address_id = 9999
        request = self.factory.get(reverse('checkout:review_order',
                                         kwargs={'address_id': invalid_address_id,
                                                'payment_method': 'credit_card'}))
        request.user = self.user
        response = review_order(request, invalid_address_id, 'credit_card')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('checkout:shipping_address'))
        
        # Test invalid payment method
        request = self.factory.get(reverse('checkout:review_order',
                                         kwargs={'address_id': self.address.id,
                                                'payment_method': 'invalid_method'}))
        request.user = self.user
        response = review_order(request, self.address.id, 'invalid_method')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('checkout:payment_method',
                                             kwargs={'address_id': self.address.id}))

    def test_checkout_success_view(self):
        request = self.factory.get(reverse('checkout:checkout_success'))
        request.user = self.user
        response = checkout_success(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/success.html')

    def test_checkout_confirmation_view(self):
        request = self.factory.get(reverse('checkout:checkout_confirmation'))
        request.user = self.user
        response = checkout_confirmation(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/confirmation.html')

    def test_generate_order_number(self):
        # Test order number generation
        order_number = generate_order_number()
        self.assertTrue(order_number.startswith('ORD-'))
        self.assertEqual(len(order_number), 24)  # 3 chars + timestamp (14 chars) + 7 chars

    def test_order_confirmation_view(self):
        request = self.factory.get(reverse('checkout:order_confirmation', args=[self.order.id]))
        request.user = self.user
        response = order_confirmation(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/order_confirmation.html')
        
        # Test invalid order
        invalid_order_id = 9999
        request = self.factory.get(reverse('checkout:order_confirmation', args=[invalid_order_id]))
        request.user = self.user
        response = order_confirmation(request, invalid_order_id)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart:cart_view'))
        request = self.factory.post(reverse('checkout:request_order_cancellation', args=[self.order.id]), {
            'reason': 'Not needed anymore'
        })
        request.user = self.user
        response = request_order_cancellation(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(OrderCancellation.objects.filter(order=self.order).exists())

    def test_start_checkout_view(self):
        request = self.factory.get(reverse('checkout:start_checkout'))
        request.user = self.user
        response = start_checkout(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/start.html')

    def test_shipping_address_view(self):
        request = self.factory.get(reverse('checkout:shipping_address'))
        request.user = self.user
        response = shipping_address(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/shipping_address.html')

    def test_payment_method_view(self):
        request = self.factory.get(reverse('checkout:payment_method', args=[self.address.id]))
        request.user = self.user
        response = payment_method(request, self.address.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/payment_method.html')

    def test_review_order_view(self):
        request = self.factory.get(reverse('checkout:review_order', args=[self.address.id, 'credit_card']))
        request.user = self.user
        response = review_order(request, self.address.id, 'credit_card')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/review.html')

    def test_checkout_success_view(self):
        request = self.factory.get(reverse('checkout:checkout_success'))
        request.user = self.user
        response = checkout_success(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/success.html')

    def test_checkout_confirmation_view(self):
        request = self.factory.get(reverse('checkout:checkout_confirmation'))
        request.user = self.user
        response = checkout_confirmation(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/confirmation.html')

    def test_checkout_shipping_view(self):
        request = self.factory.get(reverse('checkout:checkout_shipping'))
        request.user = self.user
        response = checkout_shipping(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/shipping.html')

    def test_checkout_review_view(self):
        request = self.factory.get(reverse('checkout:checkout_review'))
        request.user = self.user
        response = checkout_review(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout/review.html')
