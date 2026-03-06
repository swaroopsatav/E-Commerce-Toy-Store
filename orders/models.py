from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
from django.db import transaction
from django.core.validators import MinValueValidator
from products.models import Product

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        db_index=True,
        to_field='id'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        db_index=True,
        validators=[
            MinValueValidator(0, message='Total amount cannot be negative')
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending',
        db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    address = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
        db_index=True
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['total_amount']),
        ]

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    def clean(self):
        if self.total_amount < 0:
            raise ValidationError('Total amount cannot be negative')
        if self.shipping_amount < 0:
            raise ValidationError('Shipping amount cannot be negative')
        if self.tax_amount < 0:
            raise ValidationError('Tax amount cannot be negative')
        if self.status not in dict(self.STATUS_CHOICES):
            raise ValidationError(f'Invalid status: {self.status}')
        if self.payment_status not in dict(self.PAYMENT_STATUS_CHOICES):
            raise ValidationError(f'Invalid payment status: {self.payment_status}')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def calculate_total(self):
        """Calculate the total amount for the order."""
        with transaction.atomic():
            items_total = sum(item.total_price() for item in self.order_items.all())
            self.tax_amount = items_total * Decimal('0.18')
            self.total_amount = items_total + self.shipping_amount + self.tax_amount
            self.save()
            return self.total_amount

    def cancel(self):
        """Cancel the order."""
        if self.status == 'Delivered':
            raise ValidationError('Cannot cancel a delivered order')
        self.status = 'Cancelled'
        self.payment_status = 'Cancelled'
        self.save()

    def deliver(self):
        """Mark the order as delivered."""
        if self.status != 'Pending':
            raise ValidationError('Can only deliver pending orders')
        self.status = 'Delivered'
        self.payment_status = 'Paid'
        self.save()


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items',
        db_index=True
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items_product',
        db_index=True
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1, message='Quantity must be at least 1')
        ]
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_index=True,
        validators=[
            MinValueValidator(0, message='Price cannot be negative')
        ]
    )

    class Meta:
        ordering = ['-order__created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
            models.Index(fields=['quantity']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def clean(self):
        if self.quantity < 1:
            raise ValidationError('Quantity must be at least 1')
        if self.price < 0:
            raise ValidationError('Price cannot be negative')
        if self.product.stock < self.quantity:
            raise ValidationError(
                f'Only {self.product.stock} units of {self.product.name} are available'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def total_price(self):
        """Calculate the total price for this order item."""
        return self.quantity * self.price

    def update_quantity(self, new_quantity):
        """Update the quantity of this order item."""
        if new_quantity < 1:
            raise ValidationError('Quantity must be at least 1')
        if self.product.stock < new_quantity:
            raise ValidationError(
                f'Only {self.product.stock} units of {self.product.name} are available'
            )
        self.quantity = new_quantity
        self.save()
        self.order.calculate_total()
