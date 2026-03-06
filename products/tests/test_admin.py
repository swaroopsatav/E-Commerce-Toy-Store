from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .models import Category, Product, ProductImage, CategoryImage
from .admin import CategoryAdmin, ProductAdmin

class AdminTestCase(TestCase):
    def setUp(self):
        # Create test user and log in
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='testadmin',
            email='admin@test.com',
            password='testpassword'
        )
        self.client.login(username='testadmin', password='testpassword')

        # Create test data
        self.parent_category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            is_active=True
        )
        self.child_category = Category.objects.create(
            name='Smartphones',
            slug='smartphones',
            parent=self.parent_category,
            is_active=True
        )

        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test product description',
            price=100.00,
            stock=10,
            is_active=True
        )
        self.product.categories.add(self.child_category)

    def test_category_admin(self):
        """Test Category admin functionality"""
        admin = CategoryAdmin(Category, AdminSite())
        category = Category.objects.get(name='Electronics')

        # Test product count
        self.assertEqual(admin.product_count(category), 1)

        # Test string representation
        self.assertEqual(str(category), 'Electronics')

        # Test get ancestors
        child = Category.objects.get(name='Smartphones')
        ancestors = child.get_ancestors()
        self.assertEqual(len(ancestors), 1)
        self.assertEqual(ancestors[0].name, 'Electronics')

    def test_product_admin(self):
        """Test Product admin functionality"""
        admin = ProductAdmin(Product, AdminSite())
        product = Product.objects.get(name='Test Product')

        # Test final price
        self.assertEqual(admin.final_price(product), '₹100.00')

        # Test stock status
        self.assertEqual(
            admin.stock_status(product),
            '<span class="badge bg-success">In Stock</span>'
        )

    def test_category_list_view(self):
        """Test Category list view"""
        response = self.client.get(reverse('admin:products_category_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Electronics')
        self.assertContains(response, 'Smartphones')

    def test_product_list_view(self):
        """Test Product list view"""
        response = self.client.get(reverse('admin:products_product_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, '₹100.00')

    def test_category_add_view(self):
        """Test adding a new category"""
        response = self.client.post(
            reverse('admin:products_category_add'),
            {
                'name': 'New Category',
                'slug': 'new-category',
                'is_active': True
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='New Category').exists())

    def test_product_add_view(self):
        """Test adding a new product"""
        response = self.client.post(
            reverse('admin:products_product_add'),
            {
                'name': 'New Product',
                'slug': 'new-product',
                'description': 'New product description',
                'price': 200.00,
                'stock': 5,
                'is_active': True,
                'categories': [self.child_category.id]
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='New Product').exists())

    def test_category_image_upload(self):
        """Test category image upload"""
        image = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        response = self.client.post(
            reverse('admin:products_categoryimage_add'),
            {
                'category': self.parent_category.id,
                'image': image,
                'alt_text': 'Test image',
                'is_primary': True
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CategoryImage.objects.exists())

    def test_product_image_upload(self):
        """Test product image upload"""
        image = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        response = self.client.post(
            reverse('admin:products_productimage_add'),
            {
                'product': self.product.id,
                'image': image,
                'alt_text': 'Test image',
                'is_primary': True
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProductImage.objects.exists())

    def test_category_edit(self):
        """Test editing a category"""
        category = Category.objects.get(name='Electronics')
        response = self.client.post(
            reverse('admin:products_category_change', args=[category.id]),
            {
                'name': 'Updated Category',
                'slug': 'updated-category',
                'is_active': True
            }
        )
        self.assertEqual(response.status_code, 302)
        category.refresh_from_db()
        self.assertEqual(category.name, 'Updated Category')

    def test_product_edit(self):
        """Test editing a product"""
        product = Product.objects.get(name='Test Product')
        response = self.client.post(
            reverse('admin:products_product_change', args=[product.id]),
            {
                'name': 'Updated Product',
                'slug': 'updated-product',
                'description': 'Updated description',
                'price': 150.00,
                'stock': 15,
                'is_active': True,
                'categories': [self.child_category.id]
            }
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.name, 'Updated Product')

    def test_category_delete(self):
        """Test deleting a category"""
        category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            is_active=True
        )
        response = self.client.post(
            reverse('admin:products_category_delete', args=[category.id]),
            {'post': 'yes'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(name='Test Category').exists())

    def test_product_delete(self):
        """Test deleting a product"""
        product = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            description='Test product description',
            price=50.00,
            stock=5,
            is_active=True
        )
        response = self.client.post(
            reverse('admin:products_product_delete', args=[product.id]),
            {'post': 'yes'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(name='Test Product 2').exists())
