from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .views import (
    PasswordChangeView,
    PasswordChangeDoneView,
    PasswordResetFormView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)

app_name = 'users'
urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home, name='home'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('order_history/', views.order_history, name='order_history'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('payment_history/', views.payment_history, name='payment_history'),
    path('wishlist/', views.wishlist, name='wishlist'),
    
    # Password Management
    path('password_change/', PasswordChangeView.as_view(), name='password_change'),
    path('password_change_done/', PasswordChangeDoneView.as_view(template_name='users/password_change_done.html'), name='password_change_done'),
    path('password_reset/', PasswordResetFormView.as_view(), name='password_reset'),
    path('password_reset_done/', PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path('password_reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset_complete/', PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),
]
