import os
import uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from .models import Product, Category, ProductImage, CategoryImage
from .views import validate_image_size, product_image_path, category_image_path

class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            description="Test category description",
            is_active=True
        )
        
        self.product = Product.objects.create(
            name="Test Product",
            description="Test product description",
            price=Decimal('100.00'),
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
        
        self.product_image = ProductImage.objects.create(
            product=self.product,
            image=self.image,
            is_primary=True
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.price, Decimal('100.00'))
        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.product.is_active)
        self.assertTrue(self.product.is_featured)
        self.assertEqual(self.product.categories.count(), 1)

    def test_product_str_method(self):
        self.assertEqual(str(self.product), "Test Product")

    def test_product_final_price(self):
        self.assertEqual(self.product.final_price(), Decimal('100.00'))
        
        # Test with discount
        self.product.discount_price = Decimal('80.00')
        self.product.save()
        self.assertEqual(self.product.final_price(), Decimal('80.00'))

    def test_product_image_creation(self):
        self.assertEqual(self.product_image.product, self.product)
        self.assertTrue(self.product_image.image.name.startswith("product_images/"))
        self.assertTrue(self.product_image.is_primary)

    def test_product_image_str_method(self):
        self.assertEqual(str(self.product_image), f"Image for {self.product.name}")

    def test_category_creation(self):
        self.assertEqual(self.category.name, "Test Category")
        self.assertEqual(self.category.description, "Test category description")
        self.assertTrue(self.category.is_active)
        self.assertEqual(self.category.products.count(), 1)

    def test_category_str_method(self):
        self.assertEqual(str(self.category), "Test Category")

    def test_category_image_creation(self):
        category_image = CategoryImage.objects.create(
            category=self.category,
            image=self.image,
            is_primary=True
        )
        self.assertEqual(category_image.category, self.category)
        self.assertTrue(category_image.image.name.startswith("category_images/"))
        self.assertTrue(category_image.is_primary)

    def test_category_image_str_method(self):
        category_image = CategoryImage.objects.create(
            category=self.category,
            image=self.image,
            is_primary=True
        )
        self.assertEqual(str(category_image), f"Image for {self.category.name}")

    def test_image_validation(self):
        # Test valid image
        valid_image = SimpleUploadedFile(
            'valid.jpg',
            b'file_content',
            content_type='image/jpeg'
        )
        self.assertIsNone(validate_image_size(valid_image))
        
        # Test invalid image size
        with self.assertRaises(ValidationError):
            large_image = SimpleUploadedFile(
                'large.jpg',
                b'file_content',
                content_type='image/jpeg'
            )
            validate_image_size(large_image)
        
        # Test invalid image format
        with self.assertRaises(ValidationError):
            invalid_image = SimpleUploadedFile(
                'invalid.txt',
                b'file_content',
                content_type='text/plain'
            )
            validate_image_size(invalid_image)

    def test_product_image_path(self):
        path = product_image_path(self.product_image, 'test.jpg')
        self.assertTrue(path.startswith('product_images/'))
        self.assertIn(str(self.product.id), path)

    def test_category_image_path(self):
        category_image = CategoryImage.objects.create(
            category=self.category,
            image=self.image,
            is_primary=True
        )
        path = category_image_path(category_image, 'test.jpg')
        self.assertTrue(path.startswith('category_images/'))
        self.assertIn(str(self.category.id), path)

    def test_product_slug_generation(self):
        self.assertTrue(self.product.slug)
        self.assertEqual(self.product.slug, slugify(self.product.name))

    def test_category_slug_generation(self):
        self.assertTrue(self.category.slug)
        self.assertEqual(self.category.slug, slugify(self.category.name))

    def test_product_updated_at(self):
        initial_updated_at = self.product.updated_at
        self.product.description = "Updated description"
        self.product.save()
        self.product.refresh_from_db()
        self.assertTrue(self.product.updated_at > initial_updated_at)

    def test_category_updated_at(self):
        initial_updated_at = self.category.updated_at
        self.category.description = "Updated description"
        self.category.save()
        self.category.refresh_from_db()
        self.assertTrue(self.category.updated_at > initial_updated_at)
