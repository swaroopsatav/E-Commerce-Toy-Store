from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home_view, name='home_view'),

    # Product URLs
    path('product/create/', views.product_create, name='product_create'),
    path('product/update/<uuid:product_id>/', views.product_update, name='product_update'),
    path('product/delete/<uuid:product_id>/', views.product_delete, name='product_delete'),
    path('product/detail/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('product/search/', views.product_search, name='product_search'),
    path('product/list/', views.product_list, name='product_list'),

    # Category URLs
    path('category/create/', views.category_create, name='category_create'),
    path('category/update/<uuid:category_id>/', views.category_update, name='category_update'),
    path('category/delete/<uuid:category_id>/', views.category_delete, name='category_delete'),
    path('category/detail/<uuid:category_id>/', views.category_detail, name='category_detail'),
    path('category/search/', views.category_search, name='category_search'),
    path('category/list/', views.category_list, name='category_list'),

    # Search URLs
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
]
