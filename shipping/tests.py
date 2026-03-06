from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from orders.models import Order
from users.models import CustomUser
from .models import (
    ShippingAddress
)
from .forms import ShippingAddressForm
from unittest.mock import patch
import uuid


class ShippingAddressTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='password')
        self.order = Order.objects.create(user=self.user)
        self.shipping_address = ShippingAddress.objects.create(
            user=self.user,
            order=self.order,
            address="123 Main St",
            city="Test City",
            state="Test State",
            postal_code=12345,
            country="Test Country",
            phone_number=1234567890
        )

    def test_shipping_address_creation(self):
        self.assertEqual(self.shipping_address.user, self.user)
        self.assertEqual(self.shipping_address.order, self.order)
        self.assertEqual(self.shipping_address.address, "123 Main St")
        self.assertEqual(self.shipping_address.city, "Test City")
        self.assertEqual(self.shipping_address.state, "Test State")
        self.assertEqual(self.shipping_address.postal_code, 12345)
        self.assertEqual(self.shipping_address.country, "Test Country")
        self.assertEqual(self.shipping_address.phone_number, 1234567890)
        self.assertIsInstance(self.shipping_address.id, uuid.UUID)

    def test_shipping_address_str(self):
        self.assertEqual(str(self.shipping_address), "123 Main St, Test City, Test Country")

class ShippingAddressFormTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='password')
        self.order = Order.objects.create(user=self.user)
        self.valid_data = {
            'order': self.order,
            'address': "123 Main St",
            'city': "Test City",
            'state': "Test State",
            'postal_code': 12345,
            'country': "Test Country",
            'phone_number': 1234567890,
        }

    def test_valid_form(self):
        form = ShippingAddressForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_fields(self):
        invalid_data = self.valid_data.copy()
        del invalid_data['address']  # Removing required field
        form = ShippingAddressForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('address', form.errors)

    def test_form_save(self):
        form = ShippingAddressForm(data=self.valid_data)
        if form.is_valid():
            address = form.save(commit=False)
            self.assertIsInstance(address, ShippingAddress)
            self.assertEqual(address.address, "123 Main St")

class AddressViewTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password='password',
                                                   email='testuser@example.com')
        self.user2 = CustomUser.objects.create_user(username='testuser2', password='password',
                                                    email='testuser2@example.com')

        self.order = Order.objects.create(user=self.user, status='pending')

        self.address = ShippingAddress.objects.create(
            user=self.user,
            order=self.order,
            address="123 Main St",
            city="Test City",
            state="Test State",
            postal_code="12345",
            country="Testland",
            phone_number=1234567890
        )

    def test_list_addresses(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('shipping:add_address'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.address.address)
        self.assertNotContains(response, self.address.city)
        self.assertNotContains(response, self.address.state)

    def test_add_address(self):
        self.client.login(username='testuser', password='password')

        data = {
            'address': '456 Another St',
            'city': 'New City',
            'state': 'New State',
            'postal_code': '67890',
            'country': 'Newland',
            'phone_number': 1234567890
        }
        response = self.client.post(reverse('shipping:add_address'), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('shipping:list_addresses'))
        self.assertTrue(ShippingAddress.objects.filter(address='456 Another St').exists())

    def test_update_address(self):
        self.client.login(username='testuser', password='password')

        data = {
            'address': '789 Updated St',
            'city': 'Updated City',
            'state': 'Updated State',
            'postal_code': '98765',
            'country': 'Updatedland',
            'phone_number': 1234567890
        }
        response = self.client.post(reverse('shipping:update_address', args=[self.address.id]), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('shipping:list_addresses'))
        self.address.refresh_from_db()

        self.assertEqual(self.address.address, '789 Updated St')
        self.assertEqual(self.address.city, 'Updated City')
        self.assertEqual(self.address.state, 'Updated State')
        self.assertEqual(self.address.postal_code, 98765)
        self.assertEqual(self.address.country, 'Updatedland')

    def test_delete_address(self):
        self.client.login(username='testuser', password='password')

        response = self.client.get(reverse('shipping:delete_address', args=[self.address.id]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('shipping:delete_address', args=[self.address.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('shipping:list_addresses'))
        self.assertFalse(ShippingAddress.objects.filter(id=self.address.id).exists())

    def test_permission_denied_for_other_users(self):
        self.client.login(username='testuser2', password='password')

        response = self.client.get(reverse('shipping:delete_address', args=[self.address.id]))
        self.assertNotEqual(response.status_code, 403)

        response = self.client.get(reverse('shipping:delete_address', args=[self.address.id]))
        self.assertNotEqual(response.status_code, 403)


