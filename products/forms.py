from django import forms
from .models import Product, Category, ProductImage, CategoryImage
from django.core.exceptions import ValidationError

# Maximum image size (5MB) and allowed file extensions
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']


# Helper function to validate image size and extension
def validate_image(image):
    # Check file size
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError("The image file is too large. Maximum size is 5MB.")

    # Check file extension
    extension = image.name.split('.')[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Invalid image format. Only .jpg, .jpeg, or .png allowed.")

    return image


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['created_at', 'updated_at']  # Exclude timestamp fields
        widgets = {
            'categories': forms.CheckboxSelectMultiple,  # Enable multiple category selection
        }

    # Custom validation for additional fields can go here if needed


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']  # Exclude 'id' as it's auto-generated


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']  # Only allow the image field

    # Custom image validation for product images
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise ValidationError("No image file provided.")

        # Validate image using the helper function
        return validate_image(image)


class CategoryImageForm(forms.ModelForm):
    class Meta:
        model = CategoryImage
        fields = ['image']  # Only allow the image field

    # Custom image validation for category images
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise ValidationError("No image file provided.")

        # Validate image using the helper function
        return validate_image(image)