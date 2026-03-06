import logging
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect

from .forms import ProductForm, CategoryForm
from .models import Product, Category, ProductImage, CategoryImage

logger = logging.getLogger(__name__)

# Helper function for image handling
def handle_images(instance, image_files, model):
    for image_file in image_files:
        model.objects.create(instance=instance, image=image_file)

# Helper function for pagination
def paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset.order_by('id'), per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)

def home_view(request):
    try:
        # Get all active products
        products = Product.objects.filter(is_active=True).prefetch_related('categories', 'images')
        
        # Get featured products
        featured_products = products.filter(is_featured=True)
        
        # Get categories for navigation
        categories = Category.objects.filter(is_active=True)
        
        # Get top-selling products
        top_products = products.order_by('-stock')[:5]
        
        # Get recently added products
        recent_products = products.order_by('-created_at')[:5]
        
        context = {
            'products': products[:12],  # Show first 12 products
            'featured_products': featured_products,
            'categories': categories,
            'top_products': top_products,
            'recent_products': recent_products
        }
        
        return render(request, 'products/home.html', context)
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}")
        messages.error(request, "An error occurred while loading the page.")
        return redirect('products:home_view')

# Product detail view
def product_detail(request, slug):
    try:
        # Get product with related data
        product = get_object_or_404(
            Product.objects.prefetch_related(
                'categories', 
                'images',
                'categories__images'
            ).select_related('discount_price'),
            slug=slug,
            is_active=True
        )
        
        # Get related products (same categories)
        related_products = Product.objects.filter(
            categories__in=product.categories.all(),
            is_active=True
        ).exclude(id=product.id).distinct().order_by('-created_at')[:4]
        
        # Get all categories for navigation
        categories = Category.objects.filter(is_active=True)
        
        context = {
            'product': product,
            'related_products': related_products,
            'image_count': product.images.count(),
            'categories': categories,
            'main_image': product.images.filter(is_primary=True).first() if product.images.exists() else None
        }
        
        return render(request, 'products/product_detail.html', context)
    except Product.DoesNotExist:
        logger.error(f"Product with slug {slug} not found")
        messages.error(request, "Product not found or no longer available.")
        return redirect('products:home')
    except Exception as e:
        logger.error(f"Unexpected error in product detail view: {str(e)}")
        messages.error(request, "An error occurred while loading the product.")
        return redirect('products:home')

def product_create(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        image_files = request.FILES.getlist('images')

        if product_form.is_valid():
            product = product_form.save()
            handle_images(product, image_files, ProductImage)
            messages.success(request, 'Product created successfully!')
            #print("Product created:", product.name)  # Log the product name
            return redirect('products:product_list')
        else:
            messages.error(request, 'There was an error with your form. Please try again.')
            print("Form errors:", product_form.errors)  # Log form errors
    else:
        product_form = ProductForm()

    return render(request, 'products/product_create.html', {'product_form': product_form})

def product_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        image_files = request.FILES.getlist('images')

        if product_form.is_valid():
            product = product_form.save()
            handle_images(product, image_files, ProductImage)
            messages.success(request, 'Product updated successfully!')
            return redirect('products:product_detail', product_id=product.id)
        else:
            messages.error(request, 'There was an error with your form. Please try again.')
    else:
        product_form = ProductForm(instance=product)

    return render(request, 'products/product_update.html', {'product_form': product_form, 'product': product})

# Product delete view
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('products:product_list')
    return render(request, 'products/product_delete.html', {'product': product})

# Category detail view
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    return render(request, 'products/category_detail.html', {'category': category})

# Category create view
# noinspection PyTypeChecker
def category_create(request):
    if request.method == 'POST':
        category_form = CategoryForm(request.POST, request.FILES)
        image_files = request.FILES.getlist('images')

        if category_form.is_valid():
            category = category_form.save()
            handle_images(category, image_files, CategoryImage)
            messages.success(request, 'Category created successfully!')
            return redirect('products:category_list')
        else:
            messages.error(request, 'There was an error with your form. Please try again.')
    else:
        category_form = CategoryForm()

    return render(request, 'products/category_create.html', {'category_form': category_form})

# Category update view
# noinspection PyTypeChecker
def category_update(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category_form = CategoryForm(request.POST, request.FILES, instance=category)
        image_files = request.FILES.getlist('images')

        if category_form.is_valid():
            category = category_form.save()
            handle_images(category, image_files, CategoryImage)
            messages.success(request, 'Category updated successfully!')
            return redirect('products:category_detail', category_id=category.id)
        else:
            messages.error(request, 'There was an error with your form. Please try again.')
    else:
        category_form = CategoryForm(instance=category)

    return render(request, 'products/category_update.html', {'category_form': category_form, 'category': category})

# Category delete view
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('products:category_list')
    return render(request, 'products/category_delete.html', {'category': category})

# Product list view with pagination
def product_list(request):
    """
    List all products with optional filtering and sorting.
    """
    # Get query parameters
    search_query = request.GET.get('search', '').strip()
    category_slug = request.GET.get('category')
    min_price = request.GET.get('min_price', 0)
    max_price = request.GET.get('max_price', 10000)
    sort_by = request.GET.get('sort_by', 'created_at')
    
    try:
        min_price = float(min_price)
        max_price = float(max_price)
    except ValueError:
        min_price = 0
        max_price = 10000

    # Base query with prefetch
    products = Product.objects.prefetch_related('categories', 'images').filter(is_active=True)

    # Apply filters
    if search_query:
        search_query = search_query.strip()
        if search_query:
            # Search across multiple fields including category fields
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(categories__name__icontains=search_query) |
                Q(categories__description__icontains=search_query)
            ).distinct()

    if category_slug:
        try:
            category = Category.objects.get(slug=category_slug)
            products = products.filter(categories=category)
        except Category.DoesNotExist:
            messages.error(request, f"Category '{category_slug}' not found.")
            category_slug = None

    if min_price <= max_price:
        products = products.filter(price__gte=min_price, price__lte=max_price)
    else:
        messages.error(request, "Invalid price range.")
        min_price = 0
        max_price = 10000

    # Apply sorting
    if sort_by not in ['created_at', '-created_at', 'price', '-price']:
        sort_by = 'created_at'
    products = products.order_by(sort_by)

    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except Paginator.PageNotAnInteger:
        page_obj = paginator.page(1)
    except Paginator.EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Get all categories for the sidebar
    categories = Category.objects.filter(is_active=True)

    # Get search suggestions if there's a search query
    if search_query:
        search_suggestions = Product.objects.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        ).distinct()[:5]
    else:
        search_suggestions = []

    context = {
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'search_query': search_query,
        'selected_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'categories': categories,
        'search_suggestions': search_suggestions
    }

    return render(request, 'products/product_list.html', context)

def search_suggestions(request):
    """
    Return search suggestions for the given query.
    """
    query = request.GET.get('q', '').strip()
    suggestions = []
    
    if query:
        # Get product suggestions
        product_suggestions = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).values_list('name', flat=True).distinct()[:5]
        
        # Get category suggestions
        category_suggestions = Category.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).values_list('name', flat=True).distinct()[:5]
        
        # Combine suggestions
        suggestions = list(set(list(product_suggestions) + list(category_suggestions)))
        
        # Sort suggestions by relevance
        suggestions.sort(key=lambda x: x.lower().startswith(query.lower()), reverse=True)
        suggestions = suggestions[:5]  # Limit to 5 suggestions

    return JsonResponse({'suggestions': suggestions})

# Product search view
def product_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return product_list(request)  # Redirect to product list if query is empty

    products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)).select_related()
    page_obj = paginate(request, products, per_page=10)
    return render(request, 'products/product_list.html', {'page_obj': page_obj, 'query': query})

# Category list view with pagination
def category_list(request):
    categories = Category.objects.all().only('id', 'name')
    page_obj = paginate(request, categories, per_page=10)
    return render(request, 'products/category_list.html', {'page_obj': page_obj})

# Category search view
def category_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return category_list(request)  # Redirect to category list if query is empty

    categories = Category.objects.filter(Q(name__icontains=query)).only('id', 'name')
    page_obj = paginate(request, categories, per_page=10)
    return render(request, 'products/category_list.html', {'page_obj': page_obj, 'query': query})
