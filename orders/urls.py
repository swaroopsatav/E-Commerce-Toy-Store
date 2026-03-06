from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    # Main Views
    path('', views.order_home, name='home'),
    # Order Views
    path('order_history/', views.order_history, name='order_history'),
    path('order_cancel/<uuid:order_id>/', views.cancel_order, name='order_cancel'),
    path('order_checkout/', views.order_checkout, name='order_checkout'),
    path('track_order/<uuid:order_id>/', views.order_track, name='order_track'),
    path('order_details/<uuid:order_id>/', views.order_details, name='order_details'),
    path('order_confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order_summary/<uuid:order_id>/', views.order_summary, name='order_summary'),
    # User Dashboard
    path('user_dashboard/', views.user_dashboard, name='user_dashboard'),
    # Admin Views
    path('admin/orders/order/export/csv/', views.export_orders_csv, name='export_orders_csv'),
    path('admin/orders/order/export/xlsx/', views.export_orders_xlsx, name='export_orders_xlsx'),
    path('import_export_csv/', views.import_export_csv, name='import_export_csv'),
    path('change_list/', views.change_list_view, name='change_list'),
]
