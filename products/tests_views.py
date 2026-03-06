import os
from io import BytesIO
from PIL import Image
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from .models import Product, Category, ProductImage, CategoryImage
from .views import home_view, product_detail, product_create, product_update, product_delete

class ProductViewsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Product',
            description='Test product description',
            price=100.00,
            stock=10,
            is_active=True,
            is_featured=True
        )
        self.product.categories.add(self.category)
        
        # Create test image
        image = Image.new('RGB', (100, 100))
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        self.image = SimpleUploadedFile(
            'test.jpg',
            image_io.read(),
            content_type='image/jpeg'
        )
        
        # Create test product image
        self.product_image = ProductImage.objects.create(
            product=self.product,
            image=self.image,
            is_primary=True
        )
        
    def add_messages_middleware(self, request):
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request

    def test_home_view(self):
        request = self.factory.get(reverse('products:home'))
        response = home_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/home.html')
        self.assertIn('products', response.context)
        self.assertIn('featured_products', response.context)
        self.assertIn('categories', response.context)
        self.assertIn('top_products', response.context)
        self.assertIn('recent_products', response.context)

    def test_product_detail_view(self):
        request = self.factory.get(reverse('products:product_detail', args=[self.product.slug]))
        response = product_detail(request, self.product.slug)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_detail.html')
        self.assertIn('product', response.context)
        self.assertIn('related_products', response.context)
        self.assertIn('image_count', response.context)
        self.assertIn('categories', response.context)

    def test_product_detail_view_nonexistent_product(self):
        request = self.factory.get(reverse('products:product_detail', args=['nonexistent']))
        response = product_detail(request, 'nonexistent')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:home'))

    def test_product_create_view(self):
        request = self.factory.post(reverse('products:product_create'), {
            'name': 'New Product',
            'description': 'New product description',
            'price': 200.00,
            'stock': 20,
            'is_active': True,
            'is_featured': False,
            'categories': [self.category.id],
            'images': [self.image]
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = product_create(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='New Product').exists())

    def test_product_update_view(self):
        request = self.factory.post(reverse('products:product_update', args=[self.product.id]), {
            'name': 'Updated Product',
            'description': 'Updated description',
            'price': 150.00,
            'stock': 15,
            'is_active': True,
            'is_featured': False,
            'categories': [self.category.id],
            'images': [self.image]
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = product_update(request, self.product.id)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Product')

    def test_product_delete_view(self):
        product_id = self.product.id
        request = self.factory.post(reverse('products:product_delete', args=[product_id]))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = product_delete(request, product_id)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(id=product_id).exists())

    def test_product_list_view(self):
        request = self.factory.get(reverse('products:product_list'))
        response = product_list(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_list.html')
        self.assertIn('products', response.context)
        self.assertIn('page_obj', response.context)

    def test_product_search_view(self):
        request = self.factory.get(reverse('products:product_search') + '?q=test')
        response = product_search(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_search.html')
        self.assertIn('products', response.context)
        self.assertIn('query', response.context)

    def test_category_list_view(self):
        request = self.factory.get(reverse('products:category_list'))
        response = category_list(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/category_list.html')
        self.assertIn('categories', response.context)
        self.assertIn('page_obj', response.context)

    def test_category_search_view(self):
        request = self.factory.get(reverse('products:category_search') + '?q=test')
        response = category_search(request)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/category_search.html')
        self.assertIn('categories', response.context)
        self.assertIn('query', response.context)

    def test_category_detail_view(self):
        request = self.factory.get(reverse('products:category_detail', args=[self.category.id]))
        response = category_detail(request, self.category.id)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/category_detail.html')
        self.assertIn('category', response.context)
        self.assertIn('products', response.context)

    def test_category_create_view(self):
        request = self.factory.post(reverse('products:category_create'), {
            'name': 'New Category',
            'description': 'New category description',
            'is_active': True,
            'parent': self.category.id,
            'image': self.image
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = category_create(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='New Category').exists())

    def test_category_update_view(self):
        request = self.factory.post(reverse('products:category_update', args=[self.category.id]), {
            'name': 'Updated Category',
            'description': 'Updated description',
            'is_active': True,
            'parent': None,
            'image': self.image
        })
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = category_update(request, self.category.id)
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated Category')

    def test_category_delete_view(self):
        category_id = self.category.id
        request = self.factory.post(reverse('products:category_delete', args=[category_id]))
        request.user = self.user
        request = self.add_messages_middleware(request)
        response = category_delete(request, category_id)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(id=category_id).exists())
