from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.contrib.auth import get_user_model
from .models import Order, OrderItem, OrderTracking, ShippingAddress, OrderCancellation
from products.models import Product

User = get_user_model()

class OrderResource(resources.ModelResource):
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'username')
    )
    shipping_address = fields.Field(
        column_name='shipping_address',
        attribute='shipping_address',
        widget=ForeignKeyWidget(ShippingAddress, 'full_name')
    )

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'user', 'status', 'payment_status',
            'payment_method', 'shipping_address', 'tracking_number',
            'expected_delivery_date', 'subtotal', 'shipping_amount',
            'tax_amount', 'total_amount', 'created_at', 'updated_at'
        )
        export_order = fields

class OrderItemResource(resources.ModelResource):
    order = fields.Field(
        column_name='order',
        attribute='order',
        widget=ForeignKeyWidget(Order, 'order_number')
    )
    product = fields.Field(
        column_name='product',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'name')
    )

    class Meta:
        model = OrderItem
        fields = (
            'id', 'order', 'product', 'quantity', 'price',
            'status', 'created_at', 'updated_at'
        )
        export_order = fields

class OrderTrackingResource(resources.ModelResource):
    order = fields.Field(
        column_name='order',
        attribute='order',
        widget=ForeignKeyWidget(Order, 'order_number')
    )

    class Meta:
        model = OrderTracking
        fields = (
            'id', 'order', 'status', 'notes', 'location',
            'created_at', 'updated_at'
        )
        export_order = fields

@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_class = OrderResource
    list_display = (
        'order_number', 'user', 'status', 'payment_status', 'total_amount',
        'created_at', 'items_count', 'tracking_link'
    )
    list_filter = (
        'status', 'payment_status', 'payment_method', 'created_at',
        'shipping_address__city', 'shipping_address__state'
    )
    search_fields = (
        'order_number', 'user__username', 'user__email',
        'shipping_address__full_name', 'shipping_address__phone_number'
    )
    readonly_fields = (
        'order_number', 'created_at', 'updated_at', 'total_amount',
        'tracking_link'
    )
    ordering = ('-created_at',)
    fieldsets = (
        (_('Order Details'), {
            'fields': (
                'order_number', 'user', 'status', 'payment_status',
                'payment_method', 'shipping_address'
            )
        }),
        (_('Financial Details'), {
            'fields': (
                'total_amount',
            )
        }),
        (_('Order Items'), {
            'fields': ('items_list',)
        }),
        (_('Tracking'), {
            'fields': ('tracking_link',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'shipping_address'
        ).prefetch_related(
            'order_items__product', 'tracking_updates'
        )
    
    def items_count(self, obj):
        return obj.order_items.count()
    items_count.short_description = _('Items')
    
    def items_list(self, obj):
        items = obj.order_items.all()
        return format_html(
            '<ul>{}</ul>',
            ''.join(
                format_html(
                    '<li>{} × {}</li>',
                    item.product.name,
                    item.quantity
                ) for item in items
            )
        )
    items_list.short_description = _('Order Items')
    
    def tracking_link(self, obj):
        if obj.tracking_number:
            return format_html(
                '<a href="{}" target="_blank" class="btn btn-sm btn-primary">Track Order</a>',
                reverse('checkout:order_tracking', args=[obj.id])
            )
        return "-"
    tracking_link.short_description = _('Track Order')
    
    def last_tracking_update(self, obj):
        if obj.tracking_updates.exists():
            latest = obj.tracking_updates.latest('created_at')
            return format_html(
                '<span class="badge bg-{}">{}</span> <small>{}</small>',
                latest.get_status_color(),
                latest.get_status_display(),
                latest.created_at.strftime("%Y-%m-%d %H:%M")
            )
        return "-"
    last_tracking_update.short_description = _('Last Update')
    
    def update_status(self, request, queryset):
        status = request.POST.get('status')
        if not status:
            self.message_user(request, _('Please select a status.'), messages.ERROR)
            return
            
        if status not in dict(ORDER_STATUS_CHOICES):
            self.message_user(request, _('Invalid status selected.'), messages.ERROR)
            return
            
        for order in queryset:
            order.update_status(status)
            messages.success(request, _('Status updated successfully.'))
    update_status.short_description = _('Update selected orders status')
    
    actions = [update_status]

@admin.register(OrderItem)
class OrderItemAdmin(ImportExportModelAdmin):
    resource_class = OrderItemResource
    list_display = (
        'order', 'product', 'quantity', 'price', 'final_price', 'status',
        'created_at'
    )
    list_filter = ('order', 'product', 'status', 'created_at')
    search_fields = (
        'order__order_number', 'product__name', 'order__user__username'
    )
    readonly_fields = ('final_price', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def final_price(self, obj):
        return obj.quantity * obj.price
    final_price.short_description = _('Total Price')

@admin.register(OrderTracking)
class OrderTrackingAdmin(ImportExportModelAdmin):
    resource_class = OrderTrackingResource
    list_display = (
        'order', 'status', 'notes', 'location', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'order__order_number', 'order__user__username', 'notes', 'location'
    )
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(ShippingAddress)
class ShippingAddressAdmin(ImportExportModelAdmin):
    list_display = (
        'full_name', 'user', 'city', 'state', 'pincode', 'phone_number',
        'is_default', 'created_at'
    )
    list_filter = (
        'city', 'state', 'country', 'is_default', 'created_at'
    )
    search_fields = (
        'user__username', 'full_name', 'phone_number', 'pincode'
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Address Details'), {
            'fields': (
                'user', 'full_name', 'phone_number', 'email',
                'address_line1', 'address_line2', 'city', 'state',
                'pincode', 'country', 'is_default'
            )
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(OrderCancellation)
class OrderCancellationAdmin(ImportExportModelAdmin):
    list_display = (
        'order', 'status', 'reason', 'requested_at', 'approved_at',
        'rejected_at'
    )
    list_filter = ('status', 'requested_at', 'approved_at', 'rejected_at')
    search_fields = (
        'order__order_number', 'order__user__username', 'reason'
    )
    readonly_fields = (
        'order', 'requested_at', 'approved_at', 'rejected_at'
    )
    ordering = ('-requested_at',)
    
    fieldsets = (
        (_('Cancellation Details'), {
            'fields': (
                'order', 'status', 'reason', 'requested_at',
                'approved_at', 'rejected_at'
            )
        }),
    )


