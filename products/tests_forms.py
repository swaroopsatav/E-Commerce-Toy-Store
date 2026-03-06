from django.test import TestCase
from .forms import ProductForm, CategoryForm, ProductImageForm, CategoryImageForm
from .models import Product, Category

class ProductFormTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            description="Test category description",
            is_active=True
        )

    def test_product_form_valid(self):
        form_data = {
            'name': 'Test Product',
            'description': 'Test product description',
            'price': '100.00',
            'stock': 10,
            'is_active': True,
            'is_featured': False,
            'categories': [self.category.id]
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_product_form_invalid_price(self):
        form_data = {
            'name': 'Test Product',
            'description': 'Test product description',
            'price': '-100.00',  # Invalid price
            'stock': 10,
            'is_active': True,
            'is_featured': False,
            'categories': [self.category.id]
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_product_form_invalid_stock(self):
        form_data = {
            'name': 'Test Product',
            'description': 'Test product description',
            'price': '100.00',
            'stock': -1,  # Invalid stock
            'is_active': True,
            'is_featured': False,
            'categories': [self.category.id]
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('stock', form.errors)

class CategoryFormTest(TestCase):
    def test_category_form_valid(self):
        form_data = {
            'name': 'Test Category',
            'description': 'Test category description',
            'is_active': True,
            'parent': None
        }
        form = CategoryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_category_form_invalid_name(self):
        form_data = {
            'name': '',  # Empty name
            'description': 'Test category description',
            'is_active': True,
            'parent': None
        }
        form = CategoryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

class ProductImageFormTest(TestCase):
    def test_product_image_form_valid(self):
        # Create a test image
        image = SimpleUploadedFile(
            'test.jpg',
            b'file_content',
            content_type='image/jpeg'
        )
        form = ProductImageForm(files={'image': image})
        self.assertTrue(form.is_valid())

    def test_product_image_form_invalid_image(self):
        # Create an invalid image (too large)
        image = SimpleUploadedFile(
            'test.jpg',
            b'file_content' * 1024 * 1024 * 6,  # 6MB file
            content_type='image/jpeg'
        )
        form = ProductImageForm(files={'image': image})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

class CategoryImageFormTest(TestCase):
    def test_category_image_form_valid(self):
        # Create a test image
        image = SimpleUploadedFile(
            'test.jpg',
            b'file_content',
            content_type='image/jpeg'
        )
        form = CategoryImageForm(files={'image': image})
        self.assertTrue(form.is_valid())

    def test_category_image_form_invalid_image(self):
        # Create an invalid image (wrong format)
        image = SimpleUploadedFile(
            'test.txt',
            b'file_content',
            content_type='text/plain'
        )
        form = CategoryImageForm(files={'image': image})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)
