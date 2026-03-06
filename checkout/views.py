from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test

from orders.models import Order
from .models import OrderItem, OrderTracking, OrderCancellation
from shipping.models import ShippingAddress
from cart.models import Cart, CartItem
from products.models import Product
from .forms import CheckoutForm
from users.models import CustomUser

# Constants
ORDER_STATUS_CHOICES = {
    'Pending': 'Pending',
    'Delivered': 'Delivered',
    'Cancelled': 'Cancelled'
}
PAYMENT_STATUS_CHOICES = {
    'Pending': 'Pending',
    'Paid': 'Paid',
    'Cancelled': 'Cancelled'
}

@login_required
def order_tracking(request, order_id):
    """View to track order status and updates"""
    try:
        order = Order.objects.select_related('shipping_address', 'cart')\
            .prefetch_related('order_items', 'tracking_updates')\
            .get(id=order_id, user=request.user)
            
        tracking_updates = order.tracking_updates.order_by('-created_at')
        context = {
            'order': order,
            'tracking_updates': tracking_updates,
            'status_colors': Order.get_status_colors()
        }
        return render(request, 'checkout/tracking.html', context)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('cart:cart_detail')

@login_required
def update_order_status(request, order_id):
    """Update order status with validation and tracking"""
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')
    
    try:
        order = Order.objects.select_related('shipping_address', 'cart')\
            .get(id=order_id, user=request.user)
            
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status not in ORDER_STATUS_CHOICES:
            return JsonResponse({'success': False, 'error': 'Invalid status'})
            
        with transaction.atomic():
            order.update_status(new_status, notes)
            messages.success(request, 'Order status updated successfully')
            return JsonResponse({'success': True})
            
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_order_tracking(request, order_id):
    """Get order tracking updates with optimized queries and caching"""
    try:
        # Use select_related and prefetch_related to optimize queries
        order = Order.objects.select_related('user', 'shipping_address').get(
            id=order_id,
            user=request.user
        )
        
        # Check cache first
        cache_key = f'order_tracking_{order_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse(cached_data)
        
        # Get tracking history with optimized query
        tracking_history = OrderTracking.objects.filter(
            order=order
        ).select_related('created_by').order_by('-created_at')
        
        tracking_data = [
            {
                'status': entry.status,
                'notes': entry.notes,
                'created_at': entry.created_at.isoformat(),
                'created_by': entry.created_by.username
            }
            for entry in tracking_history
        ]
        
        # Cache the tracking data for 5 minutes
        cache.set(cache_key, {
            'tracking': tracking_data,
            'current_status': order.status,
            'updated_at': order.updated_at.isoformat(),
            'last_updated': timezone.now().isoformat()
        }, 300)
        
        return JsonResponse({
            'tracking': tracking_data,
            'current_status': order.status,
            'updated_at': order.updated_at.isoformat(),
            'last_updated': timezone.now().isoformat()
        })
        
    except Order.DoesNotExist:
        logger.error(f"Attempt to get tracking for non-existent order: {order_id}")
        return JsonResponse({'error': 'Order not found'}, status=404)
        
    except Exception as e:
        logger.error(f"Failed to get order tracking: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get tracking information',
            'details': str(e)
        }, status=500)

@login_required
def request_order_cancellation(request, order_id):
    """Request order cancellation with validation"""
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')
    
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, 'Cancellation reason is required')
            return redirect('checkout:order_tracking', order_id)
            
        if order.status not in ['pending', 'processing']:
            messages.error(request, 'Cannot cancel order in current status')
            return redirect('checkout:order_tracking', order_id)
            
        with transaction.atomic():
            cancellation = OrderCancellation.objects.create(
                order=order,
                reason=reason
            )
            
            messages.success(request, 'Cancellation request submitted successfully')
            return redirect('checkout:order_tracking', order_id)
            
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('cart:cart_detail')

@login_required
def start_checkout(request):
    """Start the checkout process"""
    try:
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('cart:cart_detail')
            
        shipping_addresses = ShippingAddress.objects.filter(
            user=request.user
        ).order_by('-is_default', '-created_at')
        
        context = {
            'cart': cart,
            'shipping_addresses': shipping_addresses,
            'total_items': cart.items.count(),
            'total_amount': cart.calculate_total_price()
        }
        return render(request, 'checkout/start.html', context)
    except Cart.DoesNotExist:
        messages.error(request, 'Cart not found')
        return redirect('cart:cart_detail')

@login_required
def shipping_address(request):
    """Manage shipping addresses"""
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Shipping address saved successfully')
            return redirect('checkout:shipping_address')
    else:
        form = CheckoutForm()
    
    shipping_addresses = ShippingAddress.objects.filter(
        user=request.user
    ).order_by('-is_default', '-created_at')
    
    context = {
        'form': form,
        'shipping_addresses': shipping_addresses,
        'default_address': shipping_addresses.filter(is_default=True).first()
    }
    return render(request, 'checkout/shipping_address.html', context)

@login_required
def payment_method(request, address_id):
    """Select payment method and create order with enhanced security and error handling"""
    try:
        # Validate user authentication
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to continue')
            return redirect('users:login')
            
        # Validate address ownership
        address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
        
        # Validate cart existence
        cart = get_object_or_404(Cart, user=request.user)
        if not cart.items.exists():
            messages.error(request, 'Your cart is empty')
            return redirect('cart:cart_detail')
            
        if request.method == 'POST':
            payment_method = request.POST.get('payment_method')
            
            # Validate payment method
            if payment_method not in PAYMENT_METHOD_CHOICES:
                messages.error(request, 'Invalid payment method')
                return redirect('checkout:payment_method', address_id)
                
            # Validate address
            if not address.is_valid_for_shipping():
                messages.error(request, 'Shipping address is not valid')
                return redirect('checkout:shipping_address')
                
            # Validate COD eligibility
            if payment_method == 'cash_on_delivery' and not address.is_valid_for_cod():
                messages.error(request, 'Cash on Delivery not available in this area')
                return redirect('checkout:payment_method', address_id)
                
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=address,
                    cart=cart,
                    payment_method=payment_method,
                    status='pending',
                    order_number=generate_order_number()
                )
                
                # Calculate and validate totals
                order.calculate_total()
                if order.total_amount <= 0:
                    raise ValueError('Order total cannot be zero or negative')
                    
                # Create initial tracking update
                OrderTracking.objects.create(
                    order=order,
                    status='pending',
                    notes='Order created and pending payment'
                )
                
                # Update cart status
                cart.status = 'checkout'
                cart.save()
                
                return redirect('checkout:review_order', order.id)
                
    except Exception as e:
        logger.error(f"Payment method selection failed: {str(e)}")
        messages.error(request, 'An error occurred during payment processing')
        return redirect('cart:cart_detail')
    
    context = {
        'address': address,
        'cart': cart,
        'payment_methods': PAYMENT_METHOD_CHOICES,
        'total_amount': cart.calculate_total_price()
    }
    return render(request, 'checkout/payment_method.html', context)

@login_required
def review_order(request, order_id):
    """Review order details before final submission with enhanced security and error handling"""
    try:
        # Validate order ownership and status
        order = get_object_or_404(
            Order.objects.select_related('shipping_address', 'cart')
            .prefetch_related('order_items', 'tracking_updates'),
            id=order_id,
            user=request.user,
            status='pending'
        )
        
        if request.method == 'POST':
            with transaction.atomic():
                # Process payment
                try:
                    # Simulate payment processing
                    if order.payment_method == 'cash_on_delivery':
                        order.payment_status = 'paid'
                        order.status = 'confirmed'
                        order.save()
                        
                        # Create tracking update
                        OrderTracking.objects.create(
                            order=order,
                            status='confirmed',
                            notes='Order confirmed for Cash on Delivery'
                        )
                        
                        # Update order items status
                        for item in order.order_items.all():
                            item.update_status('confirmed')
                            item.save()
                            
                            # Update product stock
                            if item.product.stock >= item.quantity:
                                item.product.stock -= item.quantity
                                item.product.save()
                            else:
                                raise ValueError(f'Insufficient stock for {item.product.name}')
                                
                        # Send confirmation email
                        send_order_confirmation_email(order)
                        
                        messages.success(request, 'Order placed successfully')
                        return redirect('checkout:order_confirmation', order_id=order.id)
                    
                    # For online payments, redirect to payment gateway
                    else:
                        # Implement actual payment gateway integration here
                        # For now, simulate successful payment
                        order.payment_status = 'paid'
                        order.status = 'processing'
                        order.save()
                        
                        # Create tracking update
                        OrderTracking.objects.create(
                            order=order,
                            status='processing',
                            notes='Order processing started'
                        )
                        
                        # Update order items status
                        for item in order.order_items.all():
                            item.update_status('processing')
                            item.save()
                            
                        messages.success(request, 'Payment successful')
                        return redirect('checkout:checkout_success')
                        
                except Exception as e:
                    logger.error(f"Payment processing failed for order {order.id}: {str(e)}")
                    messages.error(request, 'Payment processing failed. Please try again.')
                    return redirect('checkout:review_order', order_id)
                    
        # Cache order details for 5 minutes
        cache_key = f'order_review_{order_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return render(request, 'checkout/review.html', cached_data)
            
        # Calculate and cache totals
        total_items = order.order_items.count()
        total_amount = order.total_amount
        shipping_amount = order.shipping_amount
        tax_amount = order.tax_amount
        
        context = {
            'order': order,
            'total_items': total_items,
            'total_amount': total_amount,
            'shipping_amount': shipping_amount,
            'tax_amount': tax_amount
        }
        
        # Cache the data
        cache.set(cache_key, context, 300)
        return render(request, 'checkout/review.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('cart:cart_detail')
    except Exception as e:
        logger.error(f"Order review failed: {str(e)}")
        messages.error(request, 'An error occurred while reviewing your order')
        return redirect('cart:cart_detail')

@login_required
def checkout_success(request):
    """Display checkout success page"""
    return render(request, 'checkout/success.html')

@login_required
def checkout_confirmation(request):
    """Display checkout confirmation page"""
    return render(request, 'checkout/confirmation.html')

@login_required
def checkout_shipping(request):
    """Display shipping information page"""
    return render(request, 'checkout/shipping.html')

def checkout_review(request):
    """Display order review page"""
    return render(request, 'checkout/review.html')

# Admin views
@require_POST
@user_passes_test(lambda u: u.is_staff)
def admin_update_order_status(request, order_id):
    """Admin view to update order status"""
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status not in ORDER_STATUS_CHOICES:
            return JsonResponse({'success': False, 'error': 'Invalid status'})
            
        with transaction.atomic():
            order.update_status(new_status, notes)
            return JsonResponse({'success': True})
            
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@user_passes_test(lambda u: u.is_staff)
def admin_refund_order(request, order_id):
    """Admin view to process order refund"""
    try:
        order = Order.objects.get(id=order_id)
        if order.payment_status != 'paid':
            return JsonResponse({
                'success': False,
                'error': 'Order has not been paid'
            })
            
        with transaction.atomic():
            # Process refund (implement refund logic here)
            order.payment_status = 'refunded'
            order.status = 'cancelled'
            order.save()
            
            # Create tracking update
            OrderTracking.objects.create(
                order=order,
                status='cancelled',
                notes='Order refunded'
            )
            
            return JsonResponse({'success': True})
            
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'})

# Helper functions
def get_cart(user):
    """Get or create cart for user"""
    try:
        cart = Cart.objects.get(user=user)
        return cart
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=user)
        return cart

def validate_address(address):
    """Validate shipping address"""
    errors = []
    
    # Validate phone number
    if not address.phone_number.isdigit() or len(address.phone_number) != 10:
        errors.append("Phone number must be 10 digits")
        
    # Validate pincode
    if not address.pincode.isdigit() or len(address.pincode) != 6:
        errors.append("Pincode must be 6 digits")
        
    # Validate city and state
    if not address.city or not address.city.strip():
        errors.append("City is required")
    if not address.state or not address.state.strip():
        errors.append("State is required")
        
    return errors

@login_required
def review_order(request, address_id, payment_method):
    """Review order details before final submission"""
    try:
        address = ShippingAddress.objects.get(id=address_id, user=request.user)
        cart = get_cart(request.user)
        
        if not cart or not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('cart:cart_detail')
            
        # Validate payment method
        if payment_method not in dict(PAYMENT_METHOD_CHOICES):
            messages.error(request, "Invalid payment method")
            return redirect('checkout:payment_method', address_id=address_id)
            
        # Validate COD for this address
        if payment_method == 'cash_on_delivery' and not address.is_valid_for_cod():
            messages.error(request, "Cash on Delivery is not available for this address")
            return redirect('checkout:payment_method', address_id=address_id)
            
        # Calculate totals
        subtotal = cart.calculate_total_price()
        shipping_cost = address.calculate_shipping_cost()
        tax = subtotal * 0.18
        total = subtotal + shipping_cost + tax
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            cart=cart,
            payment_method=payment_method,
            total_amount=total
        )

        # Create order items
        for cart_item in cart.cart_items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.final_price
            )
        
        # Create initial tracking update
        OrderTracking.objects.create(
            order=order,
            status='pending',
            notes='Order created and pending processing'
        )
        
        # Generate tracking number
        order.tracking_number = f'TRACK-{timezone.now().strftime("%Y%m%d%H%M%S")}-{order.id}'
        order.save()
        
        # Update product stock
        for cart_item in cart.cart_items.all():
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()
        
        # Calculate totals
        order.calculate_total()
        
        # Clear cart
        cart.clear()
        
        # Update order status based on payment method
        if payment_method == 'cash_on_delivery':
            order.status = 'confirmed'
            order.save()
            
            # Send order confirmation email
            send_order_confirmation_email(order)
            
            return redirect('checkout:order_confirmation', order_id=order.id)
        else:
            # For online payments, redirect to payment gateway
            return redirect('payment:process_payment', order_id=order.id)

    except ShippingAddress.DoesNotExist:
        messages.error(request, "Invalid shipping address")
        return redirect('checkout:shipping_address')
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('checkout:review_order', 
                      address_id=address_id, 
                      payment_method=payment_method)
    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        messages.error(request, "Failed to process order. Please try again.")
        return redirect('checkout:review_order', 
                      address_id=address_id, 
                      payment_method=payment_method)

    return render(request, 'checkout/review.html', {
        'address': address,
        'cart': cart,
        'payment_method': payment_method,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'total': total
    })
@login_required
def order_confirmation(request, order_id):
    """Show order confirmation page"""
    try:
        order = Order.objects.select_related('shipping_address').prefetch_related(
            'order_items__product',
            'tracking_updates'
        ).get(id=order_id, user=request.user)
        
        # Get latest tracking update
        latest_tracking = order.tracking_updates.order_by('-created_at').first()
        
        return render(request, 'checkout/order_confirmation.html', {
            'order': order,
            'latest_tracking': latest_tracking
        })
    except Order.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect('cart:cart_view')

# Helper functions
def generate_order_number():
    """Generate a unique order number."""
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"ORD-{timestamp}"

@login_required
def update_order_status(request, order_id):
    """Update order status via AJAX with enhanced security and validation"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    try:
        # Use select_related to optimize query
        order = Order.objects.select_related('user', 'shipping_address', 'cart').get(
            id=order_id,
            user=request.user
        )
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if not new_status:
            return JsonResponse({'error': 'Status is required'}, status=400)
            
        if new_status not in dict(ORDER_STATUS_CHOICES):
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
        # Validate status transitions
        current_status = order.status
        valid_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': []
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            return JsonResponse({
                'error': f'Cannot change status from {current_status} to {new_status}'
            }, status=400)
            
        with transaction.atomic():
            order.status = new_status
            order.updated_at = timezone.now()
            order.save()
            
            # Create tracking entry
            OrderTracking.objects.create(
                order=order,
                status=new_status,
                notes=notes,
                created_by=request.user
            )
            
            # Update order items status
            order_items = OrderItem.objects.filter(order=order)
            for item in order_items:
                item.status = new_status
                item.save()
            
            # Send notification
            if new_status == 'delivered':
                send_delivery_notification(order)
            elif new_status == 'cancelled':
                send_cancellation_notification(order)
            
        return JsonResponse({
            'success': True,
            'status': new_status,
            'updated_at': order.updated_at.isoformat()
        })
        
    except Order.DoesNotExist:
        logger.error(f"Attempt to update non-existent order: {order_id}")
        return JsonResponse({'error': 'Order not found'}, status=404)
        
    except Exception as e:
        logger.error(f"Order status update failed: {str(e)}")
        return JsonResponse({
            'error': 'Failed to update order status',
            'details': str(e)
        }, status=500)

@login_required
def get_order_tracking(request, order_id):
    """Get order tracking updates"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        tracking_updates = order.tracking_updates.all().order_by('-created_at')
        
        return JsonResponse({
            'status': 'success',
            'tracking': [
                {
                    'status': update.status,
                    'status_display': update.get_status_display(),
                    'notes': update.notes,
                    'created_at': update.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'status_color': update.get_status_color()
                }
                for update in tracking_updates
            ],
            'current_status': {
                'status': order.status,
                'status_display': order.get_status_display(),
                'status_color': order.get_status_color()
            }
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Order not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Order tracking failed: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get tracking information'
        }, status=500)

@login_required
def request_order_cancellation(request, order_id):
    """Request order cancellation"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=400)
        
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            return JsonResponse({
                'status': 'error',
                'message': 'Cancellation reason is required'
            }, status=400)
            
        if order.status not in ['pending', 'processing']:
            return JsonResponse({
                'status': 'error',
                'message': 'Cannot cancel order in current status'
            }, status=400)
            
        with transaction.atomic():
            cancellation = OrderCancellation.objects.create(
                order=order,
                reason=reason
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Cancellation request submitted successfully',
                'cancellation_id': cancellation.id
            })
            
    except Order.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Order not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Order cancellation failed: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to process cancellation request'
        }, status=500)

@login_required
def checkout_success(request):
    """Display checkout success page"""
    return render(request, 'checkout/success.html')

@login_required
def checkout_confirmation(request):
    """Display checkout confirmation page"""
    try:
        cart = get_cart(request.user)
        cart_items = cart.items.all()
        shipping_address = ShippingAddress.objects.filter(user=request.user).last()
        
        if not cart_items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('cart:cart_detail')
            
        if not shipping_address:
            messages.warning(request, "Please add a shipping address first")
            return redirect('checkout:shipping_address')
            
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        
        if request.method == 'POST':
            return redirect('checkout:checkout_payment')
            
        return render(request, 'checkout/checkout_confirmation.html', {
            'cart_items': cart_items,
            'total_price': total_price,
            'shipping_address': shipping_address,
        })
        
    except Exception as e:
        logger.error(f"Checkout confirmation failed: {str(e)}")
        messages.error(request, "Failed to load checkout confirmation. Please try again.")
        return redirect('cart:cart_detail')

@login_required
def checkout_shipping(request):
    """Display and handle shipping address form"""
    try:
        # Use select_related to optimize query
        shipping_address = ShippingAddress.objects.filter(
            user=request.user
        ).select_related('user').last()
        
        if request.method == 'POST':
            form = CheckoutForm(request.POST)
            if form.is_valid():
                # Validate address before saving
                address = form.save(commit=False)
                address.user = request.user
                
                # Validate phone number
                if not address.phone_number.isdigit() or len(address.phone_number) != 10:
                    form.add_error('phone_number', 'Please enter a valid 10-digit phone number')
                    return render(request, 'checkout/shipping.html', {
                        'form': form
                    })
                
                # Validate pincode
                if not address.pincode.isdigit() or len(address.pincode) != 6:
                    form.add_error('pincode', 'Please enter a valid 6-digit pincode')
                    return render(request, 'checkout/shipping.html', {
                        'form': form
                    })
                
                address.save()
                messages.success(request, "Shipping address saved successfully")
                return redirect('checkout:checkout_review')
        else:
            form = CheckoutForm(instance=shipping_address)
            
        return render(request, 'checkout/shipping.html', {
            'form': form
        })
    except Exception as e:
        logger.error(f"Shipping address processing failed: {str(e)}")
        messages.error(request, "Failed to process shipping address. Please try again.")
        return redirect('checkout:shipping_address')

@login_required
def checkout_review(request):
    """Display order review page with optimized queries and caching"""
    try:
        # Use select_related and prefetch_related to optimize queries
        cart = get_cart(request.user)
        
        if not cart or not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('cart:cart_detail')
            
        # Use select_related to optimize query
        shipping_address = ShippingAddress.objects.filter(
            user=request.user,
            is_default=True
        ).select_related('user').first()
        
        if not shipping_address:
            messages.warning(request, "Please add a shipping address first")
            return redirect('checkout:shipping_address')
            
        # Calculate totals with optimized queries
        with transaction.atomic():
            # Prefetch related items to avoid N+1 queries
            cart_items = CartItem.objects.filter(
                cart=cart
            ).select_related('product').prefetch_related('product__category')
            
            subtotal = sum(item.product.price * item.quantity for item in cart_items)
            shipping_cost = shipping_address.calculate_shipping_cost()
            tax = subtotal * Decimal('0.18')  # Use Decimal for precise calculations
            total = subtotal + shipping_cost + tax
            
            # Cache the results for 5 minutes
            cache.set(f'cart_totals_{request.user.id}', {
                'subtotal': str(subtotal),
                'shipping_cost': str(shipping_cost),
                'tax': str(tax),
                'total': str(total)
            }, 300)
        
        return render(request, 'checkout/review.html', {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'shipping_cost': shipping_cost,
            'tax': tax,
            'total': total,
            'shipping_address': shipping_address
        })
    except Exception as e:
        logger.error(f"Checkout review failed: {str(e)}")
        messages.error(request, "Failed to process checkout review. Please try again.")
        return redirect('cart:cart_detail')
