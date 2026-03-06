import logging
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from .models import UserProfile, Wishlist
from .forms import ProfileForm, PasswordResetForm, SetPasswordForm
from orders.models import Order, OrderItem
from products.models import Product

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
@login_required
def profile(request):
    """Display and update user's profile.

    This view handles both displaying the user's profile and updating it.
    It ensures that user details are properly synchronized between the
    UserProfile and User models.
    """
    try:
        profile = get_object_or_404(UserProfile, user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Update profile
                    profile = form.save(commit=False)
                    profile.save()
                    
                    # Update user details
                    user = request.user
                    user.first_name = form.cleaned_data.get('first_name', user.first_name)
                    user.last_name = form.cleaned_data.get('last_name', user.last_name)
                    user.email = form.cleaned_data.get('email', user.email)
                    user.save()
                    
                    messages.success(request, "Profile updated successfully!")
                    return redirect('users:profile')
            except Exception as e:
                logger.error(f"Profile update error: {str(e)}")
                messages.error(request, "An error occurred while updating profile")
        else:
            messages.error(request, "Please correct the errors below")
    else:
        form = ProfileForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email
        })

    return render(request, 'users/profile.html', {
        'form': form,
        'profile': profile
    })

@require_http_methods(["GET", "POST"])
@login_required
def home(request):
    """User home page."""
    try:
        return render(request, 'users/home.html', {'user': request.user})
    except Exception as e:
        logger.error(f"Home page error: {str(e)}")
        messages.error(request, "An error occurred while loading the home page")
        return redirect('users:login')

def register(request):
    """User registration view."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, "Registration successful!")
                return redirect('users:profile')
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                messages.error(request, "An error occurred during registration")
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})

@require_http_methods(["GET", "POST"])
def login_view(request):
    """Custom user login view."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            try:
                user = form.get_user()
                login(request, user)
                messages.success(request, "Login successful!")
                return redirect('users:profile')
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                messages.error(request, "An error occurred during login")
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

@require_http_methods(["GET"])
def logout_view(request):
    """Custom user logout view."""
    try:
        logout(request)
        messages.success(request, "You have been logged out")
        return redirect('users:home')
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        messages.error(request, "An error occurred during logout")
        return redirect('users:home')

@require_http_methods(["GET"])
@login_required
def dashboard(request):
    """User dashboard home page.

    This view displays the user's dashboard with recent orders and payment history.
    """
    try:
        profile = request.user.profile
        
        # Get recent orders
        recent_orders = Order.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        # Get payment history
        payments = Payment.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        # Get wishlist count
        wishlist_count = request.user.wishlist.count()
        
        return render(request, 'users/dashboard.html', {
            'profile': profile,
            'recent_orders': recent_orders,
            'payments': payments,
            'wishlist_count': wishlist_count
        })
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found")
        return redirect('users:profile')
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        messages.error(request, "Failed to load dashboard")
        return redirect('users:home')

class PasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')

    def form_valid(self, form):
        messages.success(self.request, "Password reset successful!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below")
        return super().form_invalid(form)

class PasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'

    def get(self, request, *args, **kwargs):
        messages.success(request, "Password reset complete! You can now log in")
        return super().get(request, *args, **kwargs)

@require_http_methods(["GET", "POST"])
@login_required
def profile(request):
    """Display and update user's profile."""
    try:
        profile = get_object_or_404(UserProfile, user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Update profile
                    profile = form.save(commit=False)
                    profile.save()
                    
                    # Update user details
                    user = request.user
                    user.first_name = form.cleaned_data['first_name']
                    user.last_name = form.cleaned_data['last_name']
                    user.email = form.cleaned_data['email']
                    user.save()
                    
                    messages.success(request, "Profile updated successfully")
                    return redirect('users:profile')
            except Exception as e:
                logger.error(f"Profile update error: {str(e)}")
                messages.error(request, "An error occurred while updating profile")
        else:
            messages.error(request, "Please correct the errors below")
    else:
        form = ProfileForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email
        })
    
    return render(request, 'users/profile.html', {
        'form': form,
        'profile': profile
    })

@login_required
def order_history(request):
    """View user's order history"""
    try:
        orders = Order.objects.filter(
            user=request.user
        ).select_related('shipping_address').prefetch_related(
            'order_items__product',
            'payments'
        ).order_by('-created_at')
        
        return render(request, 'users/order_history.html', {
            'orders': orders
        })
    except Exception as e:
        logger.error(f"Order history error: {str(e)}")
        messages.error(request, "Failed to load order history")
        return redirect('users:dashboard')

@login_required
def order_detail(request, order_id):
    """View details of a specific order"""
    try:
        order = Order.objects.select_related(
            'shipping_address',
            'payments'
        ).prefetch_related(
            'order_items__product',
            'order_items__product__category'
        ).get(
            id=order_id,
            user=request.user
        )
        
        return render(request, 'users/order_detail.html', {
            'order': order
        })
    except Order.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect('users:order_history')
    except Exception as e:
        logger.error(f"Order detail error: {str(e)}")
        messages.error(request, "Failed to load order details")
        return redirect('users:order_history')

@login_required
def payment_history(request):
    """View user's payment history"""
    try:
        payments = Payment.objects.filter(
            user=request.user
        ).select_related(
            'order',
            'order__shipping_address'
        ).prefetch_related(
            'order__order_items__product'
        ).order_by('-created_at')
        
        return render(request, 'users/payment_history.html', {
            'payments': payments
        })
    except Exception as e:
        logger.error(f"Payment history error: {str(e)}")
        messages.error(request, "Failed to load payment history")
        return redirect('users:dashboard')

@login_required
def wishlist(request):
    """View user's wishlist"""
    try:
        wishlist = request.user.wishlist.all()
        return render(request, 'users/wishlist.html', {
            'wishlist': wishlist
        })
    except Exception as e:
        logger.error(f"Wishlist error: {str(e)}")
        messages.error(request, "Failed to load wishlist")
        return redirect('users:dashboard')


class PasswordChangeView(PasswordChangeView):
    template_name = 'users/password_change_form.html'
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        return render(self.request, self.template_name, {'form': form, 'success': True})

    def form_invalid(self, form):
        return render(self.request, self.template_name, {'form': form, 'error': True})


class PasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'users/password_change_done.html'
    success_url = reverse_lazy('products:home_view')

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class PasswordResetFormView(PasswordResetView):
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')
    subject_template_name = 'users/password_reset_subject.txt'
    from_email = settings.DEFAULT_FROM_EMAIL
    html_email_template_name = 'users/password_reset_email.html'

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': {
                'domain': self.request.get_host(),
                'protocol': 'https' if self.request.is_secure() else 'http'
            }
        }
        form.save(**opts)
        return super().form_valid(form)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {
            'form': form,
            'error': True
        })


class PasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class PasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        return redirect(self.success_url)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {'form': form, 'error': True})

class PasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
