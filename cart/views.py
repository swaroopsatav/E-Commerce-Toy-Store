from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import Cart, CartItem
from products.models import Product

@login_required
def cart_home(request):
    cart = get_cart(request.user)
    cart_items = cart.cart_items.select_related('product') if cart else []
    total_price = cart.calculate_total_price() if cart else 0

    return render(request, "cart/home.html", {
        "cart": cart,
        "cart_items": cart_items,
        "total_price": total_price
    })

@login_required
def cart_view(request):
    cart = get_cart(request.user)
    if not cart:
        return redirect('cart:cart_empty')
    
    cart_items = cart.cart_items.select_related("product")
    total_price = cart.calculate_total_price()

    # Calculate shipping and tax
    shipping = 50.00
    tax = total_price * 0.18
    grand_total = total_price + shipping + tax

    return render(request, 'cart/cart_view.html', {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price,
        'shipping': shipping,
        'tax': tax,
        'grand_total': grand_total
    })

@login_required
def cart_detail(request):
    cart = get_cart(request.user)
    if not cart:
        return redirect('cart:cart_empty')
    
    cart_items = cart.cart_items.select_related("product")
    total_price = cart.calculate_total_price()

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        if not product_id:
            messages.error(request, "Product ID is required")
            return redirect('cart:cart_detail')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product not found")
            return redirect('cart:cart_detail')

        if 'cart_update' in request.POST:
            quantity = int(request.POST.get('quantity', 1))
            try:
                cart_item = cart.cart_items.get(product=product)
                cart_item.update_quantity(quantity)
                messages.success(request, f"Updated quantity for {product.name}")
            except CartItem.DoesNotExist:
                messages.error(request, "Cart item not found")
            return redirect('cart:cart_detail')

        if 'remove_from_cart' in request.POST:
            cart.remove_item(product)
            messages.success(request, f"Removed {product.name} from cart")
            return redirect('cart:cart_detail')

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price
    })

@login_required
def add_to_cart(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect('products:product_list')

    cart = get_cart(request.user)
    try:
        cart.add_item(product)
        messages.success(request, f"Added {product.name} to cart")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('cart:cart_detail')

@login_required
def remove_from_cart(request, product_id):
    cart = get_cart(request.user)
    if not cart:
        messages.warning(request, "Cart is empty")
        return redirect('cart:cart_detail')

    try:
        product = Product.objects.get(id=product_id)
        cart.remove_item(product)
        messages.success(request, f"Removed {product.name} from cart")
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
    except CartItem.DoesNotExist:
        messages.warning(request, "Product not in cart")

    return redirect('cart:cart_detail')

@login_required
def cart_mini(request):
    cart = get_cart(request.user)
    if not cart:
        return render(request, 'cart/cart_mini.html', {
            'cart_items': [],
            'total_price': 0,
        })

    cart_items = cart.cart_items.select_related("product")
    total_price = cart.calculate_total_price()

    return render(request, 'cart/cart_mini.html', {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price,
    })

@login_required
def cart_empty(request):
    cart = get_cart(request.user)
    if cart:
        cart.clear()
        messages.info(request, "Cart has been emptied")
    else:
        messages.warning(request, "Cart is already empty")

    return redirect('cart:cart_detail')

@login_required
def cart_update(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        
        if not product_id or not quantity:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
        try:
            product = Product.objects.get(id=product_id)
            cart = get_cart(request.user)
            
            if not cart:
                return JsonResponse({'success': False, 'error': 'No active cart found'})
                
            cart_item = cart.cart_items.get(product=product)
            
            # Validate quantity
            quantity = int(quantity)
            if quantity < 1:
                return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'})
            if quantity > product.stock:
                return JsonResponse({'success': False, 'error': f'Only {product.stock} items available in stock'})
                
            cart_item.quantity = quantity
            cart_item.save()
            
            cart_total = cart.calculate_total_price()
            shipping = 50.00
            tax = cart_total * 0.18
            grand_total = cart_total + shipping + tax
            
            return JsonResponse({
                'success': True,
                'cart_total': f'₹{cart_total:.2f}',
                'item_total': f'₹{cart_item.total_price:.2f}',
                'grand_total': f'₹{grand_total:.2f}'
            })
            
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not in cart'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def get_cart(user):
    """Get or create the user's active cart."""
    cart = Cart.objects.filter(user=user, is_active=True).first()
    if not cart:
        cart = Cart.objects.create(user=user)
    return cart
