from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def send_payment_confirmation_email(order, payment):
    """Send payment confirmation email to the user"""
    subject = f"Order #{order.order_number} - Payment Confirmation"
    message = f"Dear {order.shipping_address.full_name},\n\n"
    message += f"Thank you for your order! Your order #{order.order_number} has been placed successfully.\n\n"
    
    # Payment details
    message += "Payment Details:\n"
    message += f"Payment Method: {payment.get_payment_method_display()}\n"
    message += f"Amount: ₹{payment.amount}\n"
    message += f"Status: {payment.get_status_display()}\n"
    message += f"Transaction ID: {payment.transaction_id}\n\n"
    
    # Order details
    message += "Order Details:\n"
    message += f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "\nOrder Items:\n"
    for item in order.order_items.all():
        message += f"- {item.product.name} (Qty: {item.quantity}, Price: ₹{item.price})\n"
    
    message += f"\nTotal Amount: ₹{order.total_amount}\n"
    message += "\nFor Cash on Delivery orders:\n"
    message += "- You will need to pay the delivery person when you receive your order\n"
    message += "- Please have the exact amount ready\n"
    message += "- Payment must be made in cash only\n"
    
    message += "\nThank you for shopping with us!"
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.shipping_address.email],
        fail_silently=False,
    )
