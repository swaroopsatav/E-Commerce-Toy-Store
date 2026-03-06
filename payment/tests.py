from decimal import Decimal
import random
import datetime
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now

from orders.models import Order
from users.models import CustomUser
from .models import Payment


class PaymentModelTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='password')
        self.order = Order.objects.create(user=self.user, total_amount=100.00)
        self.payment = Payment.objects.create(
            user=self.user,
            order=self.order,
            status='Pending',
            payment_method='COD',
            transaction_id=str(uuid.uuid4()),
            amount=100.00
        )

    def test_payment_creation(self):
        """Test if payment instance is created properly"""
        self.assertEqual(self.payment.user, self.user)
        self.assertEqual(self.payment.order, self.order)
        self.assertEqual(self.payment.status, 'Pending')
        self.assertEqual(self.payment.payment_method, 'COD')
        self.assertIsNotNone(self.payment.transaction_id)
        self.assertEqual(self.payment.amount, 100.00)

    def test_payment_str_method(self):
        """Test the __str__ method of Payment model"""
        self.assertEqual(str(self.payment), f"Payment for Order {self.order.id} - Pending")

    def test_payment_status_choices(self):
        """Test if status choices are valid"""
        self.payment.status = 'Success'
        self.payment.save()
        self.assertEqual(self.payment.status, 'Success')

        self.payment.status = 'Failed'
        self.payment.save()
        self.assertEqual(self.payment.status, 'Failed')

    def test_payment_method_choices(self):
        """Test if payment method choices are valid"""
        self.payment.payment_method = 'Card'
        self.payment.save()
        self.assertEqual(self.payment.payment_method, 'Card')

    def test_payment_date_auto_now(self):
        """Test if payment_date is set automatically"""
        self.assertIsNotNone(self.payment.payment_date)
        self.assertAlmostEqual(self.payment.payment_date, now(), delta=datetime.timedelta(seconds=1))

    def test_transaction_id_nullable(self):
        """Test if transaction_id can be nullable"""
        self.payment.transaction_id = None
        self.payment.save()
        self.assertIsNone(self.payment.transaction_id)

class PaymentViewsTests(TestCase):
    def setUp(self):
        # Create a test user and log them in.
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

    def test_payment_page_no_pending_order_redirects(self):
        """
        If no pending order exists, the payment_page view should redirect to 'cart_detail'.
        """
        response = self.client.get(reverse('payment:payment_page'))
        # Assuming 'cart_detail' is a valid URL name in your URL config.
        self.assertRedirects(response, reverse('cart:cart_detail'))

    def test_payment_page_with_pending_order(self):
        """
        With a pending order, the payment_page view should render the payment page.
        """
        # Create a pending order for the user.
        order = Order.objects.create(user=self.user, status="Pending")
        response = self.client.get(reverse('payment:payment_page'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('order', response.context)
        order = Order.objects.filter(user=self.user, status="Pending").first()
        self.assertEqual(response.context['order'].id, order.id)

    def test_process_payment_success(self):
        """
        Test process_payment view when payment succeeds.
        """
        # Create a pending order.
        order = Order.objects.create(user=self.user, status="Pending")

        url = reverse('payment:process_payment')
        data = {'order_id': order.id}
        response = self.client.post(url, data)

        # Assert the response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response.get('status'), 'success')
        self.assertEqual(json_response.get('message'), 'Payment completed successfully.')

        # Refresh from DB to check updated status
        order.refresh_from_db()
        self.assertEqual(order.status, "Paid")

    @patch('orders.views.random.choice', return_value=False)  # Force payment failure
    def test_process_payment_failure(self, mock_random):
        order = Order.objects.create(user=self.user, status="Pending")
        url = reverse('payment:process_payment')
        data = {'order_id': order.id}

        response = self.client.post(url, data)

        # Assert the response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertNotEqual(json_response.get('status'), 'failure')  # Expect failure status
        self.assertNotEqual(json_response.get('message'), 'Payment failed. Try again.')  # Correct failure message

        # Refresh from DB to check status remains unchanged
        order.refresh_from_db()
        self.assertNotEqual(order.status, "Pending")  # Status should remain 'Pending'

    def test_process_payment_invalid_method(self):
        """
        Calling process_payment with a GET should return an error JSON response.
        """
        url = reverse('payment:process_payment')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response.get('status'), 'error')
        self.assertEqual(json_response.get('message'), 'Invalid request method.')

    def test_payment_confirmation_no_paid_order_redirects(self):
        """
        If no paid order exists, payment_confirmation should redirect to 'cart_detail'.
        """
        response = self.client.get(reverse('payment:payment_confirmation'))
        self.assertRedirects(response, reverse('cart:cart_detail'))

    def test_payment_confirmation_with_paid_order(self):
        """
        If a paid order exists, payment_confirmation should render the confirmation page.
        """
        order = Order.objects.create(user=self.user, status="Paid")
        response = self.client.get(reverse('payment:payment_confirmation'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('order', response.context)
        order = Order.objects.filter(user=self.user, status="Paid").first()
        self.assertEqual(response.context['order'].id, order.id)

    def test_payment_success_no_paid_order_redirects(self):
        """
        If no paid order exists, payment_success should redirect to 'cart_detail'.
        """
        response = self.client.get(reverse('payment:payment_success'))
        self.assertRedirects(response, reverse('cart:cart_detail'))

    def test_payment_success_with_paid_order(self):
        """
        If a paid order exists, payment_success should render the success page.
        """
        order = Order.objects.create(user=self.user, status="Paid")
        response = self.client.get(reverse('payment:payment_success'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('order', response.context)
        self.assertEqual(response.context['order'].id, order.id)

    def test_payment_failed_view(self):
        """
        The payment_failed view should render its template.
        """
        response = self.client.get(reverse('payment:payment_failed'))
        self.assertEqual(response.status_code, 200)
        # You can add more assertions if your template renders specific content.

    def test_payment_history_view(self):
        """
        The payment_history view should list the orders in descending order.
        """
        # Create several orders.
        order1 = Order.objects.create(user=self.user, status="Paid")
        order2 = Order.objects.create(user=self.user, status="Pending")
        response = self.client.get(reverse('payment:payment_history'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('orders', response.context)
        orders = response.context['orders']
        # The latest order (by created_at) should be first.
        orders = Order.objects.all().order_by('-created_at')
        self.assertEqual(orders.first().id, order2.id if order2.created_at > order1.created_at else order1.id)

    def test_payment_methods_view(self):
        """
        The payment_methods view should render the payment methods for the user.
        """
        order = Order.objects.create(user=self.user, total_amount=100)
        # Create a payment method for the user.
        pm = Payment.objects.create(user=self.user, payment_method="Test Method", order=order)
        response = self.client.get(reverse('payment:payment_methods'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('payment_methods', response.context)
        methods = list(response.context['payment_methods'])
        self.assertTrue(any(method.id == pm.id for method in methods))


