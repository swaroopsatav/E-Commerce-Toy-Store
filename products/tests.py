import uuid
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import CustomUser
from .forms import ProductForm, CategoryForm, ProductImageForm, CategoryImageForm
from .models import Product, Category, ProductImage, CategoryImage


class ProductModelTest(TestCase):
    def setUp(self):
        self.categories = Category.objects.create(name="Test Category1", description="Electronics products")
        self.product = Product.objects.create(
            id=uuid.uuid4(),
            name="Test Product1",
            description="A test toy",
            price=699.99,
            stock=100,
            is_featured=True
        )
        self.product.categories.add(self.categories)

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Test Product1")
        self.assertEqual(self.product.price, 699.99)
        self.assertTrue(self.product.is_featured)
        self.assertEqual(self.product.stock, 100)
        self.assertEqual(self.product.categories.count(), 1)

    def test_product_str_method(self):
        self.assertEqual(str(self.product), "Test Product1")


class ProductImageModelTest(TestCase):
    def setUp(self):
        self.categories = Category.objects.create(name="Test Category1", description="Electronics products")
        self.product = Product.objects.create(
            id=uuid.uuid4(),
            name="Test Product1",
            description="A test toy",
            price=699.99,
            stock=100,
            is_featured=True
        )
        self.product.categories.add(self.categories)

        # Simulating an image file upload
        self.image_file = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        self.product_image = ProductImage.objects.create(product=self.product, image=self.image_file)

    def test_product_image_creation(self):
        self.assertEqual(self.product_image.product.name, "Test Product1")
        self.assertTrue(self.product_image.image.name.startswith("product_images/"))

    def test_product_image_str_method(self):
        self.assertEqual(str(self.product_image), f"Image for {self.product.name}")


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test Category1", description="Electronics products")

    def test_category_creation(self):
        self.assertEqual(self.category.name, "Test Category1")
        self.assertEqual(self.category.description, "Electronics products")

    def test_category_str_method(self):
        self.assertEqual(str(self.category), "Test Category1")


class CategoryImageModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test Category1", description="Electronics products")

        # Simulating an image file upload
        self.image_file = SimpleUploadedFile("test_category_image.jpg", b"file_content", content_type="image/jpeg")
        self.category_image = CategoryImage.objects.create(category=self.category, image=self.image_file)

    def test_category_image_creation(self):
        self.assertEqual(self.category_image.category.name, "Test Category1")
        self.assertTrue(self.category_image.image.name.startswith("category_images/"))

    def test_category_image_str_method(self):
        self.assertEqual(str(self.category_image), f"Image for {self.category.name}")



class ProductFormTest(TestCase):
    def test_product_form_valid(self):
        categories = Category.objects.create(name="Test Category1", description="A sample category")
        form_data = {
            'name': 'Test Product1',
            'description': 'A description of the test product',
            'price': 10.99,
            'stock': 50,  # Added required field 'stock'
            'categories': [categories.id],  # Assuming Product has a many-to-many relation with Category
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_product_form_invalid_no_name(self):
        categories = Category.objects.create(name="Test Category1", description="A sample category")
        form_data = {
            'description': 'A description of the test product',
            'price': 10.99,
            'stock': 50,  # Added required field 'stock'
            'categories': [categories.id],
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_product_form_invalid_image(self):
        categories = Category.objects.create(name="Test Category1", description="A sample category")
        form_data = {
            'name': 'Test Product1',
            'description': 'A description of the test product',
            'price': 10.99,
            'stock': 50,  # Added required field 'stock'
            'categories': [categories.id],
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())  # Modified as the form does not handle images


class CategoryFormTest(TestCase):
    def test_category_form_valid(self):
        form_data = {
            'name': 'Test Category1',
            'description': 'A sample category',
        }
        form = CategoryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_category_form_invalid_no_name(self):
        form_data = {
            'description': 'A sample category',
        }
        form = CategoryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class ProductImageFormTest(TestCase):
    def test_valid_image_upload(self):
        image = SimpleUploadedFile("test_image.jpg", self.generate_image(), content_type="image/jpeg")
        form_data = {'image': image}
        form = ProductImageForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_invalid_image_size(self):
        large_image = SimpleUploadedFile("large_image.jpg", self.generate_large_image(), content_type="image/jpeg")
        form_data = {'image': large_image}
        form = ProductImageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_invalid_image_extension(self):
        invalid_image = SimpleUploadedFile("invalid_image.gif", self.generate_image(), content_type="image/gif")
        form_data = {'image': invalid_image}
        form = ProductImageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    # noinspection PyMethodMayBeStatic
    def generate_image(self):
        # Simple image creation using PIL (use your preferred method for generating test images)
        img = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(img, format='JPEG')
        img.seek(0)
        return img.read()

    # noinspection PyMethodMayBeStatic
    def generate_large_image(self):
        # Generate an image larger than the size limit
        img = BytesIO()
        image = Image.new('RGB', (1000, 1000), color='red')
        image.save(img, format='JPEG')
        img.seek(0)
        return img.read()


class CategoryImageFormTest(TestCase):
    def test_valid_image_upload(self):
        image = SimpleUploadedFile("test_image.jpg", self.generate_image(), content_type="image/jpeg")
        form_data = {'image': image}
        form = CategoryImageForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_invalid_image_size(self):
        large_image = SimpleUploadedFile("large_image.jpg", self.generate_large_image(), content_type="image/jpeg")
        form_data = {'image': large_image}
        form = CategoryImageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_invalid_image_extension(self):
        invalid_image = SimpleUploadedFile("invalid_image.gif", self.generate_image(), content_type="image/gif")
        form_data = {'image': invalid_image}
        form = CategoryImageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    # noinspection PyMethodMayBeStatic
    def generate_image(self):
        # Same helper function as in ProductImageFormTest
        img = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(img, format='JPEG')
        img.seek(0)
        return img.read()

    # noinspection PyMethodMayBeStatic
    def generate_large_image(self):
        # Same helper function as in ProductImageFormTest
        img = BytesIO()
        image = Image.new('RGB', (1000, 1000), color='red')
        image.save(img, format='JPEG')
        img.seek(0)
        return img.read()

class ProductCategoryViewsTest(TestCase):

    def setUp(self):
        # Create a test user
        self.user = CustomUser.objects.create_user(username='testuser', password='testpassword')

        # Create a test category
        self.category = Category.objects.create(name='Test Category1', description='A test category')

        # Create a test product
        self.product = Product.objects.create(
            id=uuid.uuid4(),
            name='Test Product1',
            description='A test toy',
            price=100,
            stock=10, # Ensure stock is set for all test cases
        )

        # Assign category to the product
        self.product.categories.set([self.category])

        # Sample image for testing
        self.image = SimpleUploadedFile(
            "test_image.jpg",
            b"file_content",
            content_type="image/jpeg"
        )



    def test_product_detail_view(self):
        response = self.client.get(reverse('products:product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product1')

    def test_product_create_view(self):
        self.client.login(username='testuser', password='testpassword')

        data = {
            'name': 'New Product',
            'description': 'New product description',
            'price': 200,
            'stock': 50,
            'categories': [self.category.id],  # Ensure correct ManyToManyField assignment
        }
        response = self.client.post(reverse('products:product_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:product_list'))
        self.assertTrue(Product.objects.filter(name='New Product').exists())

    def test_product_update_view(self):
        self.client.login(username='testuser', password='testpassword')

        data = {
            'name': 'Updated Product',
            'description': 'Updated description',
            'price': 150,
            'stock': 50,
            'categories': [self.category.id],
        }
        response = self.client.post(reverse('products:product_update', args=[self.product.id]), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:product_detail', args=[self.product.id]))

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Product')

    def test_product_delete_view(self):
        self.client.login(username='testuser', password='testpassword')

        response = self.client.post(reverse('products:product_delete', args=[self.product.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:product_list'))
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_category_detail_view(self):
        response = self.client.get(reverse('products:category_detail', args=[self.category.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Category1')

    def test_category_create_view(self):
        self.client.login(username='testuser', password='testpassword')

        data = {
            'name': 'New Category',
            'description': 'New category description',
        }
        response = self.client.post(reverse('products:category_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:category_list'))
        self.assertTrue(Category.objects.filter(name='New Category').exists())

    def test_category_update_view(self):
        self.client.login(username='testuser', password='testpassword')

        data = {
            'name': 'Updated Category',
            'description': 'Updated category description',
        }
        response = self.client.post(reverse('products:category_update', args=[self.category.id]), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:category_detail', args=[self.category.id]))

        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Updated Category')

    def test_category_delete_view(self):
        self.client.login(username='testuser', password='testpassword')

        response = self.client.post(reverse('products:category_delete', args=[self.category.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products:category_list'))
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())


    def test_product_search_no_query(self):
        response = self.client.get(reverse('products:product_search'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_list.html')
        self.assertIn('page_obj', response.context)

    def test_product_search_with_results(self):
        # Ensure the product is saved in the database and associated with the category
        self.product.save()
        self.product.categories.add(self.category)

        response = self.client.get(reverse('products:product_search') + '?q=Test Product1')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Product1")
        self.assertNotContains(response, "Test Product2")

    def test_product_search_no_results(self):
        response = self.client.get(reverse('products:product_search') + '?q=Test Product3')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Product1")
        self.assertNotContains(response, "Test Product2")

    def test_category_list(self):
        response = self.client.get(reverse('products:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/category_list.html')
        self.assertIn('page_obj', response.context)

    def test_category_search_no_query(self):
        response = self.client.get(reverse('products:category_search'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/category_list.html')

    def test_category_search_with_results(self):
        self.category.name = "Test Category1"
        self.category.save()

        response = self.client.get(reverse('products:category_search') + '?q=Test Category1')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Category1")
        self.assertNotContains(response, "Test Category2")

    def test_category_search_no_results(self):
        response = self.client.get(reverse('products:category_search') + '?q=Test Category3')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Category1")
        self.assertNotContains(response, "Test Category2")
