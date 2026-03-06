import csv
import logging
from decimal import Decimal
import random
import openpyxl
from io import StringIO
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch

from .models import Order, OrderItem
from cart.models import Cart, CartItem
from shipping.models import ShippingAddress
from checkout.forms import CheckoutForm
from products.models import Product

logger = logging.getLogger(__name__)

@login_required
def order_home(request):
    """Display the order home page."""
    return render(request, 'orders/home.html')

@login_required
def order_checkout(request):
    """Handle order checkout process."""
    user = request.user
    
    # Calculate cart total with optimized query
    cart_items = CartItem.objects.filter(
        cart__user=user
    ).select_related('product', 'cart')
    cart_total = sum(item.product.price * item.quantity for item in cart_items)
    
    # Get shipping addresses with optimized query
    addresses = ShippingAddress.objects.filter(user=user)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create a new order
                    order = Order.objects.create(
                        user=user,
                        total_amount=cart_total,
                        status="Pending",
                        payment_status="Pending",
                        shipping_address=form.cleaned_data['shipping_address']
                    )
                    
                    # Move items from cart to the order
                    for item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=item.product.price
                        )
                    
                    # Clear the user's cart
                    cart_items.delete()
                    
                    # Recalculate total with tax and shipping
                    order.calculate_total()
                    
                    messages.success(request, 'Order created successfully')
                    return redirect('order_confirmation', order_id=order.id)
            except Exception as e:
                logger.error(f"Error during checkout: {str(e)}")
                messages.error(request, 'An error occurred during checkout')
    else:
        form = CheckoutForm()

    return render(request, 'orders/order_checkout.html', {
        'cart_total': cart_total,
        'addresses': addresses,
        'form': form,
    })

@login_required
def order_confirmation(request, order_id):
    """Display order confirmation page."""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related(
            Prefetch('order_items', OrderItem.objects.select_related('product'))
        ),
        id=order_id,
        user=request.user
    )
    return render(request, 'orders/order_confirmation.html', {'order': order})

@login_required
def order_summary(request, order_id=None):
    """Display order summary."""
    if not order_id:
        return redirect('order_history')
    
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related(
            Prefetch('order_items', OrderItem.objects.select_related('product'))
        ),
        id=order_id,
        user=request.user
    )
    return render(request, 'orders/order_summary.html', {'order': order})

@login_required
def order_history(request):
    """Display user's order history."""
    orders = Order.objects.filter(
        user=request.user
    ).select_related('user').prefetch_related(
        Prefetch('order_items', OrderItem.objects.select_related('product'))
    ).order_by('-created_at')
    
    return render(request, 'orders/order_history.html', {'orders': orders})

@login_required
def cancel_order(request, order_id):
    """Cancel an order."""
    order = get_object_or_404(
        Order.objects.select_related('user'),
        id=order_id,
        user=request.user
    )

    try:
        with transaction.atomic():
            if order.status == 'Pending':
                order.cancel()
                messages.success(request, 'Order cancelled successfully')
            else:
                messages.error(request, 'Cannot cancel a non-pending order')
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        messages.error(request, 'An error occurred while cancelling the order')

    return HttpResponseRedirect(reverse('orders:order_history'))

@login_required
def order_track(request, order_id):
    """Track order status."""
    order = get_object_or_404(
        Order.objects.select_related('user'),
        id=order_id,
        user=request.user
    )
    return render(request, 'orders/order_track.html', {'order': order})

@login_required
def order_details(request, order_id):
    """Display detailed order information."""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related(
            Prefetch('order_items', OrderItem.objects.select_related('product'))
        ),
        id=order_id,
        user=request.user
    )
    return render(request, 'orders/order_details.html', {'order': order})

@login_required
def user_dashboard(request):
    """Display user's dashboard with order history."""
    orders = Order.objects.filter(
        user=request.user
    ).select_related('user').prefetch_related(
        Prefetch('order_items', OrderItem.objects.select_related('product'))
    ).order_by('-created_at')
    
    return render(request, 'orders/user_dashboard.html', {'orders': orders})

@staff_member_required
def export_orders_csv(request):
    """Export orders to CSV format."""
    try:
        orders = Order.objects.all().select_related('user').prefetch_related(
            Prefetch('order_items', OrderItem.objects.select_related('product'))
        )
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order ID', 'User', 'Total Amount', 'Status', 'Payment Status',
            'Created At', 'Updated At', 'Shipping Amount', 'Tax Amount'
        ])
        
        for order in orders:
            writer.writerow([
                order.id, order.user.username, order.total_amount, order.status,
                order.payment_status, order.created_at, order.updated_at,
                order.shipping_amount, order.tax_amount
            ])
        
        return response
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        messages.error(request, 'Error exporting orders to CSV')
        return redirect('orders:change_list')

@staff_member_required
def export_orders_xlsx(request):
    """Export orders to Excel format."""
    try:
        orders = Order.objects.all().select_related('user').prefetch_related(
            Prefetch('order_items', OrderItem.objects.select_related('product'))
        )
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="orders.xlsx"'
        
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Orders"
        
        headers = [
            'Order ID', 'User', 'Total Amount', 'Status', 'Payment Status',
            'Created At', 'Updated At', 'Shipping Amount', 'Tax Amount'
        ]
        worksheet.append(headers)
        
        for order in orders:
            worksheet.append([
                str(order.id), order.user.username, str(order.total_amount),
                order.status, order.payment_status, str(order.created_at),
                str(order.updated_at), str(order.shipping_amount),
                str(order.tax_amount)
            ])
        
        workbook.save(response)
        return response
    except Exception as e:
        logger.error(f"Error exporting XLSX: {str(e)}")
        messages.error(request, 'Error exporting orders to Excel')
        return redirect('orders:change_list')

@staff_member_required
def import_export_csv(request):
    """Import and export orders from CSV."""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if csv_file:
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = StringIO(decoded_file)
                next(io_string)  # Skip header
                
                with transaction.atomic():
                    for line in csv.reader(io_string):
                        try:
                            user = Product.objects.get(username=line[1])
                            order = Order.objects.create(
                                id=line[0],
                                user=user,
                                total_amount=Decimal(line[2]),
                                status=line[3],
                                payment_status=line[4],
                                address=line[5]
                            )
                            messages.success(request, 'Orders imported successfully')
                        except Exception as e:
                            logger.error(f"Error importing order: {str(e)}")
                            messages.error(request, f'Error importing order: {str(e)}')
            except Exception as e:
                logger.error(f"Error during CSV import: {str(e)}")
                messages.error(request, 'Error during CSV import')
    
    return render(request, 'orders/import_export.html')

@staff_member_required
def change_list_view(request):
    """Display and manage a list of orders."""
    orders = Order.objects.all().select_related('user').prefetch_related(
        Prefetch('order_items', OrderItem.objects.select_related('product'))
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        order_id = request.POST.get('order_id')

        if action == 'delete' and order_id:
            order = get_object_or_404(Order, id=order_id)
            order.delete()
            return JsonResponse({'message': 'Order deleted successfully!'})

    return render(request, 'admin/orders/order/change_list.html', {'orders': orders})