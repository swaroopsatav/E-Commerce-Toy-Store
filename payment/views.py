from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from .models import Payment
from orders.models import Order
import logging

logger = logging.getLogger(__name__)


@login_required
def payment_home(request):
    """Payment home page"""
    order = Order.objects.filter(user=request.user, payment_status='completed').last()

    if not order:
        return redirect("checkout:checkout_home")

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        
        if not payment_method:
            messages.error(request, "Please select a payment method")
            return redirect("payment:payment_home")

        # Simulate payment processing
        order.is_paid = True
        order.payment_method = payment_method
        order.save()

        return redirect("shipping_home")

    return render(request, "payment/home.html", {"order": order})


@login_required
def payment_page(request):
    """Payment page for COD orders"""
    order_id = request.GET.get('order_id')
    
    if not order_id:
        messages.error(request, "Invalid order")
        return redirect('cart:cart_detail')

    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        if order.payment_method != 'cash_on_delivery':
            messages.error(request, "This page is only for Cash on Delivery orders")
            return redirect('cart:cart_detail')

        return render(request, 'payment/payment_page.html', {
            'order': order,
            'payment_method': 'cash_on_delivery'
        })
    except Order.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect('cart:cart_detail')


@login_required
@csrf_exempt
def process_payment(request):
    """Process payment for COD orders"""
    try:
        if request.method != 'POST':
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid request method'
            }, status=405)
        
        order_id = request.POST.get('order_id')
        payment_method = request.POST.get('payment_method')
        terms_accepted = request.POST.get('terms')
        
        if not all([order_id, payment_method, terms_accepted]):
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required parameters'
            }, status=400)
        
        # Validate terms acceptance
        if terms_accepted != 'on':
            return JsonResponse({
                'status': 'error',
                'message': 'Please agree to the payment terms'
            }, status=400)
        
        # Check if order exists and belongs to user
        order = Order.objects.select_for_update().get(
            id=order_id,
            user=request.user,
            status='pending'
        )
        
        # Validate order items
        if not order.order_items.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Order has no items'
            }, status=400)
        
        # Validate payment method
        if payment_method not in dict(PAYMENT_METHOD_CHOICES):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid payment method'
            }, status=400)
        
        # Validate shipping address
        if not order.shipping_address:
            return JsonResponse({
                'status': 'error',
                'message': 'Shipping address is required'
            }, status=400)
        
        # Validate stock availability
        for item in order.order_items.all():
            if item.quantity > item.product.stock:
                return JsonResponse({
                    'status': 'error',
                    'message': f"{item.product.name} is out of stock"
                }, status=400)
        
        # Create payment record
        with transaction.atomic():
            payment = Payment.objects.create(
                user=request.user,
                order=order,
                payment_method=payment_method,
                amount=order.total_amount
            )
            
            # Process payment based on method
            if payment_method == 'cash_on_delivery':
                # For COD, mark as pending
                payment.update_status('pending')
                
                # Update order status
                order.status = 'pending'
                order.save()
                
                # Reserve stock
                for item in order.order_items.all():
                    product = item.product
                    product.stock -= item.quantity
                    product.save()
                
                # Send confirmation email
                send_payment_confirmation_email(payment)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment initiated successfully. Your order will be delivered with Cash on Delivery option.',
                    'payment_id': str(payment.id),
                    'transaction_id': payment.transaction_id,
                    'order_number': order.order_number
                })
            else:
                # For other payment methods, implement actual payment processing
                return JsonResponse({
                    'status': 'error',
                    'message': 'Payment method not supported yet'
                }, status=400)
                
    except Order.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Order not found or already processed'
        }, status=404)
        
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
        
    except Exception as e:
        logger.error(f"Payment processing failed: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Payment processing failed. Please try again.'
        }, status=500)


@login_required
def payment_confirmation(request, payment_id):
    """Display payment confirmation page"""
    try:
        payment = Payment.objects.select_related(
            'order', 
            'order__shipping_address',
            'order__order_items__product',
            'order__order_items__product__category'
        ).get(
            id=payment_id,
            user=request.user
        )
        
        if payment.status == 'failed':
            messages.error(request, "Payment failed. Please try again.")
            return redirect('cart:cart_view')
            
        # Get order items with product details
        items = payment.order.order_items.select_related('product', 'product__category')
        
        return render(request, 'payment/payment_confirmation.html', {
            'payment': payment,
            'order': payment.order,
            'items': items
        })
    except Payment.DoesNotExist:
        messages.error(request, "Payment not found")
        return redirect('cart:cart_view')
    except Exception as e:
        logger.error(f"Payment confirmation failed: {str(e)}")
        messages.error(request, "Failed to load payment confirmation")
        return redirect('cart:cart_view')


@login_required
def payment_history(request):
    """Display payment history"""
    try:
        payments = Payment.objects.select_related(
            'order', 
            'order__shipping_address',
            'order__order_items__product',
            'order__order_items__product__category'
        ).filter(
            user=request.user
        ).order_by('-created_at')
        
        return render(request, 'payment/payment_history.html', {
            'payments': payments
        })
    except Exception as e:
        logger.error(f"Payment history failed: {str(e)}")
        messages.error(request, "Failed to load payment history")
        return redirect('cart:cart_view')
