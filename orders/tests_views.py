import os
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from django.urls import reverse

from users.models import CustomUser
from products.models import Product, Category
from cart.models import Cart, CartItem
from shipping.models import ShippingAddress
from .models import Order, OrderItem
from .views import (
    order_checkout, order_confirmation, order_summary,
    order_history, cancel_order, order_track, order_details,
    user_dashboard, export_orders_csv, export_orders_xlsx,
    import_export_csv, change_list_view
)

class OrderViewsTest(TestCase):
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

    def add_messages_middleware(self, request):
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request

    def test_order_checkout_view(self):
        request = self.factory.get(reverse('orders:order_checkout'))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = order_checkout(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_checkout.html')

    def test_order_checkout_post(self):
        request = self.factory.post(reverse('orders:order_checkout'), {
            'shipping_address': '123 Test Street'
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = order_checkout(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(user=self.user).exists())

    def test_order_confirmation_view(self):
        request = self.factory.get(reverse('orders:order_confirmation', args=[self.order.id]))
        request.user = self.user
        response = order_confirmation(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_confirmation.html')

    def test_order_summary_view(self):
        request = self.factory.get(reverse('orders:order_summary', args=[self.order.id]))
        request.user = self.user
        response = order_summary(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_summary.html')

    def test_order_history_view(self):
        request = self.factory.get(reverse('orders:order_history'))
        request.user = self.user
        response = order_history(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_history.html')

    def test_cancel_order_view(self):
        request = self.factory.post(reverse('orders:cancel_order', args=[self.order.id]))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = cancel_order(request, self.order.id)
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'Cancelled')

    def test_order_track_view(self):
        request = self.factory.get(reverse('orders:order_track', args=[self.order.id]))
        request.user = self.user
        response = order_track(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_track.html')

    def test_order_details_view(self):
        request = self.factory.get(reverse('orders:order_details', args=[self.order.id]))
        request.user = self.user
        response = order_details(request, self.order.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_details.html')

    def test_user_dashboard_view(self):
        request = self.factory.get(reverse('orders:user_dashboard'))
        request.user = self.user
        response = user_dashboard(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/user_dashboard.html')

    def test_export_orders_csv_view(self):
        request = self.factory.get(reverse('orders:export_orders_csv'))
        request.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        response = export_orders_csv(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_orders_xlsx_view(self):
        request = self.factory.get(reverse('orders:export_orders_xlsx'))
        request.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        response = export_orders_xlsx(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_import_export_csv_view(self):
        request = self.factory.post(reverse('orders:import_export_csv'), {
            'csv_file': SimpleUploadedFile(
                'test.csv',
                b'Order ID,User,Total Amount,Status\n1,testuser,200.00,Pending',
                content_type='text/csv'
            )
        })
        request.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        response = import_export_csv(request)
        self.assertEqual(response.status_code, 200)

    def test_change_list_view(self):
        request = self.factory.get(reverse('orders:change_list'))
        request.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        response = change_list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/change_list.html')
