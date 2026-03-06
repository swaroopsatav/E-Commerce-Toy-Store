from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from products.models import Product
import uuid

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carts',
        db_index=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        unique_together = ('user', 'is_active')
        ordering = ['-created_at']

    def calculate_total_price(self):
        """Calculate the total price of all items in the cart."""
        total = sum(item.total_price for item in self.cart_items.all())
        self.total_price = total
        self.tax_amount = total * Decimal('0.18')
        self.total_amount = total + self.shipping_amount + self.tax_amount
        self.save()
        return self.total_amount

    class Meta:
        unique_together = ('user', 'is_active')

    def calculate_total_price(self):
        """Calculate the total price of all items in the cart."""
        return sum(item.total_price for item in self.cart_items.all())

    def add_item(self, product, quantity=1):
        """Add or update a product in the cart."""
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        
        if quantity > product.stock:
            raise ValueError(f"Only {product.stock} units of {product.name} are available")
        
        with transaction.atomic():
            cart_item, created = CartItem.objects.select_for_update().get_or_create(
                cart=self,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                if cart_item.quantity + quantity > product.stock:
                    raise ValueError(f"Only {product.stock} units of {product.name} are available")
                cart_item.quantity += quantity
                cart_item.save()
            
            # Update cart totals
            self.calculate_total_price()
            return cart_item

    def remove_item(self, product):
        """Remove a product from the cart."""
        with transaction.atomic():
            CartItem.objects.filter(cart=self, product=product).delete()
            self.calculate_total_price()

    def clear(self):
        """Clear all items from the cart."""
        with transaction.atomic():
            self.cart_items.all().delete()
            self.total_price = 0
            self.shipping_amount = 50.00
            self.tax_amount = 0
            self.total_amount = 0
            self.save()

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='cart_items',
        db_index=True
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        db_index=True
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Price at the time of adding to cart"
    )
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('cart', 'product')

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        
        if self.price <= 0:
            raise ValidationError("Price must be greater than 0")

    def save(self, *args, **kwargs):
        # Update price to current product price when saving
        self.price = self.product.price
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.cart.user.username} - {self.product.name} - {self.quantity}"

    def update_quantity(self, quantity):
        """Update the quantity of the cart item."""
        if quantity <= 0:
            self.delete()
            return None
        
        if quantity > self.product.stock:
            raise ValueError(f"Only {self.product.stock} units of {self.product.name} are available")
        
        with transaction.atomic():
            self.quantity = quantity
            self.save()
            self.cart.calculate_total_price()
            return self


