import os.path
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.db.models import F
import uuid
from django.utils.text import slugify
from django.utils import timezone
import os
from PIL import Image

def validate_image_size(image):
    try:
        img = Image.open(image)
        width, height = img.size
        
        # Maximum dimensions (1920x1080)
        max_width = 1920
        max_height = 1080
        
        if width > max_width or height > max_height:
            raise ValidationError(
                _('Image dimensions are too large. Maximum size is %(width)sx%(height)s pixels.'),
                params={'width': max_width, 'height': max_height},
            )
            
        # Minimum dimensions (200x200)
        min_width = 200
        min_height = 200
        
        if width < min_width or height < min_height:
            raise ValidationError(
                _('Image dimensions are too small. Minimum size is %(width)sx%(height)s pixels.'),
                params={'width': min_width, 'height': min_height},
            )
            
        # Maximum file size (5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if image.size > max_size:
            raise ValidationError(
                _('Image file size is too large. Maximum size is %(size)s MB.'),
                params={'size': max_size / (1024 * 1024)},
            )
            
        # Check image format
        valid_formats = ['JPEG', 'PNG', 'WEBP']
        if img.format not in valid_formats:
            raise ValidationError(
                _('Unsupported image format. Only JPEG, PNG, and WEBP are allowed.'),
            )
            
    except Exception as e:
        logger.error(f"Image validation error: {str(e)}")
        raise ValidationError(
            _('Invalid image file: %(error)s'),
            params={'error': str(e)},
        )

def product_image_path(instance, filename):
    return os.path.join('product_images', str(instance.product.id), filename)

def category_image_path(instance, filename):
    return os.path.join('category_images', str(instance.category.id), filename)

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Required. 255 characters or fewer. Letters, numbers, and spaces only."
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text="Unique URL-friendly identifier for this category"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the category"
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='subcategories',
        on_delete=models.CASCADE,
        help_text="Parent category if this is a subcategory"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this category is active and should be displayed"
    )
    image = models.ImageField(
        upload_to='category_images',
        null=True,
        blank=True,
        help_text="Category image for display",
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp'],
                message="Only JPG, JPEG, PNG, and WEBP images are allowed"
            ),
            validate_image_size
        ]
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                name="unique_category_hierarchy",
                fields=['parent', 'name'],
                condition=models.Q(parent__isnull=False)
            ),
            models.CheckConstraint(
                name="prevent_self_reference",
                check=~models.Q(parent=models.F('id'))
            )
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:category_detail', kwargs={'slug': self.slug})

    def clean(self):
        if self.parent and self.parent == self:
            raise ValidationError("A category cannot be its own parent")
        if self.parent and self.parent.parent == self:
            raise ValidationError("Cannot create circular reference in category hierarchy")
        if self.parent and self.parent.parent and self.parent.parent.parent:
            raise ValidationError("Maximum depth of category hierarchy is 3 levels")

    def get_ancestors(self):
        """Get all ancestor categories in order from top to bottom"""
        ancestors = []
        current = self
        while current.parent:
            ancestors.append(current.parent)
            current = current.parent
        return ancestors[::-1]

    def get_descendants(self):
        """Get all descendant categories recursively"""
        descendants = []
        for child in self.subcategories.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_products(self):
        """Get all products in this category and its descendants"""
        descendants = self.get_descendants()
        return Product.objects.filter(
            categories__in=[self] + descendants
        ).distinct()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Required. 255 characters or fewer. Letters, numbers, and spaces only."
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text="Unique URL-friendly identifier for this product"
    )
    description = models.TextField(
        help_text="Detailed description of the product"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[
            MinValueValidator(0.01, message="Price must be positive and at least 0.01")
        ]
    )
    discount_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(0.01, message="Discount price must be positive and at least 0.01")
        ]
    )
    stock = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0, message="Stock cannot be negative")
        ]
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this product is active and should be displayed"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Designates whether this product is featured"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    categories = models.ManyToManyField(
        Category, 
        related_name='products',
        help_text="Categories this product belongs to"
    )
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                name="discount_price_less_than_price",
                check=models.Q(discount_price__isnull=True) | models.Q(discount_price__lt=F('price'))
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def final_price(self):
        if self.discount_price:
            return self.discount_price
        return self.price

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to=product_image_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp'],
                message="Only JPG, JPEG, PNG, and WEBP images are allowed"
            ),
            validate_image_size
        ]
    )
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
        constraints = [
            models.UniqueConstraint(
                name="unique_primary_image_per_product",
                fields=['product'],
                condition=models.Q(is_primary=True)
            )
        ]

    def __str__(self):
        return f"Image for {self.product.name}"

class CategoryImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to=category_image_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp'],
                message="Only JPG, JPEG, PNG, and WEBP images are allowed"
            ),
            validate_image_size
        ]
    )
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
        constraints = [
            models.UniqueConstraint(
                name="unique_primary_image_per_category",
                fields=['category'],
                condition=models.Q(is_primary=True)
            )
        ]

    def __str__(self):
        return f"Image for {self.category.name}"
