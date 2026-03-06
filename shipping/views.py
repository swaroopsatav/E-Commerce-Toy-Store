import csv
import logging
from decimal import Decimal
import random
import openpyxl
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import ShippingAddressForm
from .models import Product , Order
from .models import ShippingAddress
from django.views.decorators.csrf import csrf_exempt
from uuid import UUID

@login_required
def shipping_home(request):
    order = Order.objects.filter(user=request.user, payment_status='completed').last()

    if not order:
        return redirect("payment:payment_home")

    return render(request, "shipping/shipping_home.html", {"order": order})

@login_required
def list_addresses(request):
    addresses = ShippingAddress.objects.filter(user=request.user)
    return render(request, 'shipping/list_addresses.html', {'addresses': addresses})

@login_required
def add_address(request):
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address added successfully.")  # Success message
            return redirect('shipping:list_addresses')
        else:
            messages.error(request, "Please correct the errors below.")
            print(form.errors)  # Debugging form errors
    else:
        form = ShippingAddressForm()

    return render(request, 'shipping/add_address.html', {'form': form})

@login_required
def update_address(request, address_id):
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)

    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=address)  # Pre-fill form with instance
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully.")  # Success message
            return redirect('shipping:list_addresses')
        else:
            messages.error(request, "Please correct the errors below.")  # Error message
            print(form.errors)  # Debugging form errors
    else:
        form = ShippingAddressForm(instance=address)  # Pre-fill form for GET request

    return render(request, 'shipping/update_address.html', {'form': form})


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)

    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address deleted successfully.")
        return redirect('shipping:list_addresses')

    return render(request, 'shipping/delete_address.html', {'address': address})

