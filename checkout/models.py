from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
from django.db import transaction
from django.core.validators import MinLengthValidator, RegexValidator, MinValueValidator

ORDER_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('shipped', 'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
)

PAYMENT_METHOD_CHOICES = (
    ('cash_on_delivery', 'Cash on Delivery'),
    ('credit_card', 'Credit Card'),
    ('debit_card', 'Debit Card'),
    ('net_banking', 'Net Banking'),
)

PAYMENT_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('failed', 'Failed'),
)

SHIPPING_STATUS_CHOICES = (
    ('not_shipped', 'Not Shipped'),
    ('ready_for_pickup', 'Ready for Pickup'),
    ('picked_up', 'Picked Up'),
    ('in_transit', 'In Transit'),
    ('delivered', 'Delivered'),
    ('failed', 'Failed'),
)

class ShippingAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shipping_addresses',
        db_index=True
    )
    full_name = models.CharField(
        max_length=255,
        validators=[
            MinLengthValidator(2, message='Full name must be at least 2 characters')
        ]
    )
    phone_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Phone number must be 10 digits'
            )
        ]
    )
    email = models.EmailField()
    address_line1 = models.CharField(
        max_length=255,
        validators=[
            MinLengthValidator(5, message='Address line 1 must be at least 5 characters')
        ]
    )
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(
        max_length=100,
        validators=[
            MinLengthValidator(2, message='City must be at least 2 characters')
        ]
    )
    state = models.CharField(
        max_length=100,
        validators=[
            MinLengthValidator(2, message='State must be at least 2 characters')
        ]
    )
    pincode = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='Pincode must be 6 digits'
            )
        ]
    )
    country = models.CharField(max_length=100, default='India')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_default = models.BooleanField(default=False)
    is_validated = models.BooleanField(default=False)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name_plural = 'Shipping Addresses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['city']),
            models.Index(fields=['state']),
            models.Index(fields=['pincode']),
            models.Index(fields=['is_default']),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.address_line1}"

    def clean(self):
        if self.is_default:
            # Remove default status from other addresses for this user
            ShippingAddress.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)

        # Validate phone number
        if not self.phone_number.isdigit() or len(self.phone_number) != 10:
            raise ValidationError("Phone number must be a 10 digit number")

        # Validate pincode
        if not self.pincode.isdigit() or len(self.pincode) != 6:
            raise ValidationError("Pincode must be a 6 digit number")

        # Validate city and state
        if not self.city or not self.city.strip():
            raise ValidationError("City is required")
        if not self.state or not self.state.strip():
            raise ValidationError("State is required")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def validate_address(self):
        """Validate address format"""
        errors = []
        
        # Validate phone number
        if not self.phone_number.isdigit() or len(self.phone_number) != 10:
            errors.append("Phone number must be a 10 digit number")
        
        # Validate pincode
        if not self.pincode.isdigit() or len(self.pincode) != 6:
            errors.append("Pincode must be a 6 digit number")
        
        # Validate city and state
        if not self.city or not self.city.strip():
            errors.append("City is required")
        if not self.state or not self.state.strip():
            errors.append("State is required")
        
        if errors:
            return False
        return True

    def is_valid_for_shipping(self):
        """Check if address is valid for shipping"""
        # Add shipping validation logic
        # For example, check if shipping is available in the area
        return True

    def is_valid_for_cod(self):
        """Check if address is valid for Cash on Delivery"""
        # Add COD validation logic
        # For example, check if COD is available in the area
        return True

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='checkout_orders',
        db_index=True
    )
    shipping_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.SET_NULL,
        null=True,
        related_name='checkout_orders',
        db_index=True
    )
    cart = models.OneToOneField(
        'cart.Cart',
        on_delete=models.CASCADE,
        related_name='checkout_order',
        db_index=True
    )
    order_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0, message='Total amount cannot be negative')
        ]
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
        validators=[
            MinValueValidator(0, message='Shipping amount cannot be negative')
        ]
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0, message='Tax amount cannot be negative')
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['total_amount']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"

    def clean(self):
        if self.total_amount < 0:
            raise ValidationError('Total amount cannot be negative')
        if self.shipping_amount < 0:
            raise ValidationError('Shipping amount cannot be negative')
        if self.tax_amount < 0:
            raise ValidationError('Tax amount cannot be negative')
        if self.status not in dict(ORDER_STATUS_CHOICES):
            raise ValidationError(f'Invalid status: {self.status}')
        if self.payment_status not in dict(PAYMENT_STATUS_CHOICES):
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

    def update_status(self, new_status, notes=None):
        """Update order status"""
        if new_status not in dict(ORDER_STATUS_CHOICES):
            raise ValidationError(f"Invalid status: {new_status}")
        
        # Validate status transitions
        valid_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValidationError(
                f"Cannot transition from {self.status} to {new_status}"
            )
            
        with transaction.atomic():
            self.status = new_status
            self.save()
            
            # Create tracking update
            OrderTracking.objects.create(
                order=self,
                status=new_status,
                notes=notes
            )

    def get_status_color(self):
        """Get status color for display"""
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

    def get_status_badge(self):
        """Get status badge HTML"""
        color = self.get_status_color()
        return f'<span class="badge bg-{color}">{self.get_status_display()}</span>'

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items',
        db_index=True
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='order_items',
        db_index=True
    )
    quantity = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, message='Quantity must be at least 1')
        ]
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0, message='Price cannot be negative')
        ]
    )
    tracking_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    shipping_status = models.CharField(
        max_length=20,
        choices=SHIPPING_STATUS_CHOICES,
        default='not_shipped',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
            models.Index(fields=['quantity']),
            models.Index(fields=['price']),
            models.Index(fields=['status']),
            models.Index(fields=['shipping_status']),
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

    def update_status(self, new_status, notes=None):
        """Update order item status"""
        if new_status not in dict(ORDER_STATUS_CHOICES):
            raise ValidationError(f"Invalid status: {new_status}")
        
        # Validate status transitions
        valid_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValidationError(
                f"Cannot transition from {self.status} to {new_status}"
            )
            
        with transaction.atomic():
            self.status = new_status
            self.save()
            
            # Create tracking update
            OrderTracking.objects.create(
                order=self.order,
                status=new_status,
                notes=notes
            )

    def get_status_color(self):
        """Get status color for display"""
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

    def get_status_badge(self):
        """Get status badge HTML"""
        color = self.get_status_color()
        return f'<span class="badge bg-{color}">{self.get_status_display()}</span>'

class OrderTracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='tracking_updates',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        db_index=True
    )
    notes = models.TextField(blank=True, null=True)
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()}"

class OrderCancellation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='cancellation',
        db_index=True
    )
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending',
        db_index=True
    )

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['requested_at']),
        ]

    def clean(self):
        if not self.reason.strip():
            raise ValidationError('Cancellation reason is required')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def approve(self):
        """Approve cancellation request"""
        if self.status != 'pending':
            raise ValidationError('Cannot approve non-pending cancellation')
            
        with transaction.atomic():
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.save()
            
            # Update order status
            self.order.update_status('cancelled', 'Cancellation approved')

    def reject(self, reason=None):
        """Reject cancellation request"""
        if self.status != 'pending':
            raise ValidationError('Cannot reject non-pending cancellation')
            
        with transaction.atomic():
            self.status = 'rejected'
            self.rejected_at = timezone.now()
            self.save()
            
            # Create tracking update
            OrderTracking.objects.create(
                order=self.order,
                status='cancelled',
                notes=f'Cancellation rejected: {reason}' if reason else 'Cancellation rejected'
            )

    def __str__(self):
        return f"Cancellation for Order {self.order.order_number}"
