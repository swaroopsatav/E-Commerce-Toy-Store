from django.conf import settings
from django.db import models
from django.utils.timezone import now
from orders.models import Order
import uuid
from django.utils import timezone

PAYMENT_METHOD_CHOICES = (
    ('cash_on_delivery', 'Cash on Delivery'),
    ('credit_card', 'Credit Card'),
    ('debit_card', 'Debit Card'),
    ('net_banking', 'Net Banking'),
)

PAYMENT_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
)

PAYMENT_PROVIDER_CHOICES = (
    ('cod', 'Cash on Delivery'),
    ('stripe', 'Stripe'),
    ('razorpay', 'Razorpay'),
    ('paytm', 'Paytm'),
)

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    payment_provider = models.CharField(
        max_length=20,
        choices=PAYMENT_PROVIDER_CHOICES,
        default='cod'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    transaction_id = models.CharField(
        max_length=100,
        unique=True
    )
    provider_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.get_payment_method_display()}"

    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        return f"PAY{self.payment_method.upper()[0:3]}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

    def validate_payment(self):
        """Validate payment details"""
        if self.amount <= 0:
            raise ValueError("Payment amount must be greater than 0")
        
        if not self.transaction_id:
            raise ValueError("Transaction ID is required")
        
        if self.status not in dict(PAYMENT_STATUS_CHOICES):
            raise ValueError("Invalid payment status")
        
        if self.payment_method not in dict(PAYMENT_METHOD_CHOICES):
            raise ValueError("Invalid payment method")
        
        if self.order.total_amount != self.amount:
            raise ValueError("Payment amount does not match order total")

    def save(self, *args, **kwargs):
        """Save payment with validation"""
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        
        self.validate_payment()
        super().save(*args, **kwargs)

    def update_status(self, status, provider_transaction_id=None):
        """Update payment status"""
        if status not in dict(PAYMENT_STATUS_CHOICES):
            raise ValueError("Invalid payment status")
        
        self.status = status
        if provider_transaction_id:
            self.provider_transaction_id = provider_transaction_id
        self.save()

    def process_payment(self):
        """Process payment based on payment method"""
        if self.payment_method == 'cash_on_delivery':
            # For COD, mark as pending
            self.update_status('pending')
            return True
        
        # For other payment methods, implement actual payment processing
        return False

    def cancel_payment(self, reason=None):
        """Cancel payment"""
        if self.status == 'completed':
            raise ValueError("Cannot cancel completed payment")
        
        self.update_status('cancelled')
        
        # Update order status if needed
        if self.order:
            self.order.status = 'cancelled'
            self.order.save()

    def refund_payment(self, amount=None):
        """Refund payment"""
        if self.status != 'completed':
            raise ValueError("Can only refund completed payments")
        
        if amount and amount > self.amount:
            raise ValueError("Refund amount cannot exceed original amount")
        
        # Implement refund logic based on payment provider
        return False
