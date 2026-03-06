from django.contrib import admin
from .models import Order, OrderItem
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import Order
from .views import (
    export_orders_csv,
    export_orders_xlsx,
    import_export_csv,
    change_list_view,
)
from import_export.admin import ExportMixin


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price')
    list_filter = ('id', 'order', 'product', 'quantity', 'price')
    search_fields = ('id', 'order', 'product', 'quantity', 'price')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'payment_status', 'created_at', 'order_actions']
    list_filter = ('id', 'user', 'total_amount', 'status', 'payment_status', 'created_at')
    search_fields = ('id', 'user', 'total_amount', 'status', 'payment_status', 'created_at')
    change_list_template = "admin/orders/order/change_list.html"  # Corrected template path

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export/csv/', self.admin_site.admin_view(export_orders_csv), name='export_orders_csv'),
            path('export/xlsx/', self.admin_site.admin_view(export_orders_xlsx), name='export_orders_xlsx'),
            path('import-export/csv/', self.admin_site.admin_view(import_export_csv), name='import_export_csv'),
            path('manage/', self.admin_site.admin_view(change_list_view), name='order_change_list_view'),
        ]
        return custom_urls + urls

    def order_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Manage</a>&nbsp;'
            '<a class="button" href="{}">Export CSV</a>&nbsp;'
            '<a class="button" href="{}">Export XLSX</a>',
            redirect('admin:order_change_list_view').url,
            redirect('admin:export_orders_csv').url,
            redirect('admin:export_orders_xlsx').url
        )

    order_actions.short_description = 'Actions'
    order_actions.allow_tags = True




