from django.conf import settings
from django.db import models
from django.utils.timezone import now
from products.models import Product
from products.models import Category
from orders.models import Order
import uuid

class ShippingAddress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shipping_shipping_addresses')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipping_address',null=True,blank=True,db_index=True)
    address = models.CharField(db_index=True,max_length=255)
    city = models.CharField(db_index=True,max_length=100)
    state = models.CharField(db_index=True,max_length=100)
    postal_code = models.IntegerField()
    country = models.CharField(db_index=True,max_length=100)
    phone_number = models.IntegerField(db_index=True,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.address}, {self.city}, {self.country}"


