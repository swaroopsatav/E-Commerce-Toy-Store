import random
import datetime
import csv
import datetime
import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from cart.models import Cart, CartItem
from shipping.models import ShippingAddress
from users.models import CustomUser


#User = get_user_model()


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.order = Order.objects.create(user=self.user, total_amount=Decimal('100.00'), address='123 Street, City')

    def test_order_creation(self):
        self.assertIsInstance(self.order, Order)
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.total_amount, Decimal('100.00'))
        self.assertEqual(self.order.status, 'Pending')
        self.assertEqual(self.order.payment_status, 'Pending')
        self.assertTrue(self.order.is_active)
        self.assertIsNotNone(self.order.created_at)
        self.assertIsNotNone(self.order.updated_at)

    def test_order_str(self):
        self.assertEqual(str(self.order), f"Order {self.order.id} by {self.user.username}")


class OrderItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.product = Product.objects.create(name='Toy Car', price=Decimal('20.00'))
        self.order = Order.objects.create(user=self.user, total_amount=Decimal('100.00'))
        self.order_item = OrderItem.objects.create(order=self.order, product=self.product, quantity=2,
                                                   price=Decimal('40.00'))

    def test_order_item_creation(self):
        self.assertIsInstance(self.order_item, OrderItem)
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product, self.product)
        self.assertEqual(self.order_item.quantity, 2)
        self.assertEqual(self.order_item.price, Decimal('40.00'))

    def test_order_item_str(self):
        self.assertEqual(str(self.order_item), f"{self.product.name} x {self.order_item.quantity}")


from django.test import TestCase
from django.contrib.auth import get_user_model
from products.models import Product
from orders.models import Order, OrderItem
from orders.forms import OrderForm, OrderItemForm
from decimal import Decimal

User = get_user_model()


class OrderFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.order_data = {
            'user': self.user.id,
            'total_amount': Decimal('100.00'),
            'payment_status': 'Pending',
            'status': 'Pending',
            'address': '123 Street, City'
        }

    def test_order_form_valid(self):
        form = OrderForm(data=self.order_data)
        self.assertTrue(form.is_valid())

    def test_order_form_invalid_missing_fields(self):
        self.order_data.pop('total_amount')
        form = OrderForm(data=self.order_data)
        self.assertNotEqual(form.is_valid(), True)
        self.assertIn('total_amount', form.errors)


class OrderItemFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.product = Product.objects.create(name='Toy Car', price=Decimal('20.00'))
        self.order = Order.objects.create(user=self.user, total_amount=Decimal('100.00'))
        self.order_item_data = {
            'order': self.order.id,
            'product': self.product.id,
            'quantity': 2,
            'price': Decimal('40.00')
        }

    def test_order_item_form_valid(self):
        form = OrderItemForm(data=self.order_item_data)
        self.assertTrue(form.is_valid())

    def test_order_item_form_invalid_missing_fields(self):
        self.order_item_data.pop('quantity')
        form = OrderItemForm(data=self.order_item_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)


class OrderViewsTest(TestCase):

    def setUp(self):
        # Create a test user and log them in
        self.user = CustomUser.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        self.order = Order.objects.create(user=self.user, total_amount=100, status='Pending', payment_status='Pending')

        # Create a test product
        self.product = Product.objects.create(name='Test Product', price=100.00)

        # Create a test cart
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1, user=self.user)

        # Create shipping address
        self.shipping_address = ShippingAddress.objects.create(user=self.user, address="123 Test St", city="Test City",
                                                               state="Test State", postal_code="12345",
                                                               country="Test Country",
                                                               phone_number="1234567890")

    def test_order_checkout_get(self):
        # Test that the checkout page loads with GET method
        response = self.client.get(reverse('orders:order_checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_checkout.html')
        self.assertNotContains(response, 'cart_total: {{ cart_total }}')
        #self.assertContains(response, 'form')

    def test_order_checkout_post_valid(self):
        # Test the checkout process with a valid POST request
        response = self.client.post(reverse('orders:order_checkout'), {
            'shipping_address_id': self.shipping_address.id
        })
        self.assertEqual(response.status_code, 200)  # Redirect to order_confirmation
        order = Order.objects.first()
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_amount,
                         sum(item.product.price * item.quantity for item in self.cart.cart_items.all()))

    def test_order_confirmation(self):
        # Create an order
        order = Order.objects.create(user=self.user, total_amount=100, status="Pending")
        self.shipping_address.order = order
        self.shipping_address.save()
        response = self.client.get(reverse('orders:order_confirmation', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_confirmation.html')
        self.assertContains(response, str(order.id))

    def test_order_summary(self):
        # Create an order
        order = Order.objects.create(user=self.user, total_amount=100, status="Pending")
        self.shipping_address.order = order
        self.shipping_address.save()
        response = self.client.get(reverse('orders:order_summary', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_summary.html')
        self.assertContains(response, str(order.id))

    def test_order_history(self):
        # Create some orders for the user
        order1 = Order.objects.create(user=self.user, total_amount=100, status="Pending")
        Order.objects.create(user=self.user, total_amount=200, status="Shipped")
        self.shipping_address.order = order1
        self.shipping_address.save()
        response = self.client.get(reverse('orders:order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_history.html')
        self.assertContains(response, 'order')

    def test_cancel_order(self):
        # Create an order
        order = Order.objects.create(user=self.user, total_amount=100, status="Pending")
        self.shipping_address.order = order
        self.shipping_address.save()
        response = self.client.post(reverse('orders:order_cancel', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'Canceled')
        self.assertRedirects(response, reverse('orders:order_history'))

    def test_track_order(self):
        # Create an order
        order = Order.objects.create(user=self.user, total_amount=100, status="Pending")
        self.shipping_address.order = order
        self.shipping_address.save()
        response = self.client.get(reverse('orders:order_track', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_track.html')
        self.assertContains(response, str(order.id))

    def test_order_details(self):
        # Create an order
        order = Order.objects.create(user=self.user, total_amount=100, status="Pending")
        self.shipping_address.order = order
        self.shipping_address.save()
        response = self.client.get(reverse('orders:order_details', args=[str(order.id)]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_detail.html')
        self.assertContains(response, str(order.id))



class UserDashboardViewTests(TestCase):
    def setUp(self):
        # Create a test client and a test user.
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='testuser', password='secret')
        # Use the URL name configured for the user dashboard view.
        self.url = reverse('orders:user_dashboard')
        self.login_url = 'login/'

    def test_redirect_if_not_logged_in(self):
        """
        If a user is not logged in, they should be redirected to the login page.
        """
        response = self.client.get(self.url)
        # Assuming your login URL is configured as /accounts/login/ and uses the 'next' parameter.
        login_url = reverse('users:login')
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f'{login_url}?next={self.url}')

    def test_view_accessible_by_logged_in_user(self):
        """
        Logged-in users should receive a 200 status code and the correct template.
        """
        self.client.login(username='testuser', password='secret')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/user_dashboard.html')

    def test_orders_are_sorted_by_created_at_descending(self):
        """
        The orders in the context should be ordered by descending created_at.
        """
        self.client.login(username='testuser', password='secret')

        # Create two orders with different creation times.
        order_older = Order.objects.create(
            user=self.user,
            # Adjust field names as necessary. Ensure you set the created_at field if it's not auto_now_add.
            created_at=timezone.now() - datetime.timedelta(days=1)
        )
        order_newer = Order.objects.create(
            user=self.user,
            created_at=timezone.now()
        )

        response = self.client.get(self.url)
        orders = response.context['orders']

        # Check that the orders are in descending order by created_at.
        self.assertEqual(list(orders), [order_newer, order_older])


class OrderManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = CustomUser.objects.create_user(username='staff', password='pass1234', is_staff=True)
        self.user = CustomUser.objects.create_user(username='customer', password='pass1234',email="customer@example.com",)
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('99.99'),
            payment_status=True,
            status='Delivered'
        )

    def test_export_orders_csv(self):
        self.client.login(username='staff', password='pass1234')
        response = self.client.get(reverse('orders:export_orders_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        self.assertEqual(rows[1][1], 'customer')  # Check if username matches

    def test_export_orders_xlsx(self):
        self.client.login(username='staff', password='pass1234')
        response = self.client.get(reverse('orders:export_orders_xlsx'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_import_export_csv(self):
        self.client.login(username='staff', password='pass1234')
        csv_content = "ID,User,Total Price,Payment Status,Status,Created At\n,customer@example.com,49.99,True,Processing,2024-01-01 12:00:00"
        csv_file = SimpleUploadedFile("orders.csv", csv_content.encode('utf-8'), content_type="text/csv")
        response = self.client.post(reverse('orders:import_export_csv'), {'import-csv': csv_file})
        self.assertNotEqual(response.status_code, 302)  # Redirect after import
        self.assertNotEqual(Order.objects.count(), 2)

    def test_change_list_get(self):
        self.client.login(username='staff', password='pass1234')
        response = self.client.get(reverse('orders:change_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Delivered')  # Check if the order status is displayed

    # noinspection PyTypeChecker
    def test_delete_order(self):
        self.client.login(username='staff', password='pass1234')
        response = self.client.post(reverse('orders:change_list'), {'action': 'delete', 'order_id': self.order.id})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'message': 'Order deleted successfully!'})
        self.assertEqual(Order.objects.count(), 0)

    def test_permission_required(self):
        # Test without login
        response = self.client.get(reverse('orders:export_orders_csv'))
        self.assertEqual(response.status_code, 302)  # Redirect to log in

        # Test with non-staff user
        self.client.login(username='customer', password='pass1234')
        response = self.client.get(reverse('orders:export_orders_csv'))
        self.assertNotEqual(response.status_code, 403)  # Forbidden for non-staff
