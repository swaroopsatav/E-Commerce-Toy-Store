from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, MinLengthValidator, MaxLengthValidator
from django.db import models
from django.utils import timezone
import uuid
import re

class CustomUser(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        related_name="custom_users",
        blank=True,
        help_text="The groups this user belongs to.",
        db_index=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        db_index=True
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=255,
        unique=True,
        help_text="Required. 255 characters or fewer. Letters, digits and @/./+/-/_ only.",
        validators=[
            MinLengthValidator(3, "Username must be at least 3 characters long"),
            MaxLengthValidator(255, "Username must be 255 characters or fewer")
        ],
        error_messages={
            'unique': "A user with that username already exists.",
        },
        db_index=True
    )
    email = models.EmailField(
        unique=True,
        help_text="Required. Valid email address for account verification.",
        error_messages={
            'unique': "A user with that email address already exists.",
        },
        db_index=True
    )
    password = models.CharField(
        max_length=255,
        help_text="Required. Your password must be at least 8 characters long.",
        db_index=True
    )
    first_name = models.CharField(
        max_length=255,
        help_text="Required. Your first name.",
        validators=[
            MinLengthValidator(1, "First name must be at least 1 character long"),
            MaxLengthValidator(255, "First name must be 255 characters or fewer")
        ],
        db_index=True
    )
    last_name = models.CharField(
        max_length=255,
        help_text="Required. Your last name.",
        validators=[
            MinLengthValidator(1, "Last name must be at least 1 character long"),
            MaxLengthValidator(255, "Last name must be 255 characters or fewer")
        ],
        db_index=True
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="The date and time when the user joined.",
        editable=False
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The date and time when the user last logged in.",
        editable=False
    )

    def clean(self):
        super().clean()
        
        # Email validation
        if self.email:
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Enter a valid email address.'})

        # Username validation
        if self.username:
            if not re.match(r'^[\w.@+-]+$', self.username):
                raise ValidationError({
                    'username': 'Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.'
                })

        # Password validation
        if self.password:
            if len(self.password) < 8:
                raise ValidationError({
                    'password': 'Password must be at least 8 characters long'
                })

        # First name validation
        if self.first_name:
            if len(self.first_name) < 1:
                raise ValidationError({
                    'first_name': 'First name must be at least 1 character long'
                })

        # Last name validation
        if self.last_name:
            if len(self.last_name) < 1:
                raise ValidationError({
                    'last_name': 'Last name must be at least 1 character long'
                })

    def save(self, *args, **kwargs):
        # Ensure email is lowercase
        if self.email:
            self.email = self.email.lower()
        
        # Ensure username is lowercase
        if self.username:
            self.username = self.username.lower()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']


class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='profile',
        db_index=True
    )
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text='Format: 10 digit number without country code',
        validators=[
            MinLengthValidator(10, "Phone number must be 10 digits long"),
            MaxLengthValidator(10, "Phone number must be 10 digits long")
        ]
    )
    address_line_1 = models.CharField(
        max_length=255, 
        blank=True,
        help_text='Street address, P.O. box, company name, c/o'
    )
    address_line_2 = models.CharField(
        max_length=255, 
        blank=True,
        help_text='Apartment, suite, unit, building, floor, etc.'
    )
    city = models.CharField(
        max_length=100, 
        blank=True,
        help_text='City or town'
    )
    state = models.CharField(
        max_length=100, 
        blank=True,
        help_text='State or province'
    )
    postal_code = models.CharField(
        max_length=20, 
        blank=True,
        help_text='ZIP or postal code'
    )
    country = models.CharField(
        max_length=100, 
        blank=True,
        default='India',
        help_text='Country'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        help_text='Profile picture (optional)'
    )
    preferred_currency = models.CharField(
        max_length=3,
        default='INR',
        choices=[('INR', 'Indian Rupee'), ('USD', 'US Dollar'), ('EUR', 'Euro')]
    )
    language_preference = models.CharField(
        max_length=2,
        default='en',
        choices=[('en', 'English'), ('hi', 'Hindi'), ('mr', 'Marathi')]
    )
    newsletter_subscription = models.BooleanField(
        default=False,
        help_text='Subscribe to our newsletter'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        
        # Phone number validation
        if self.phone_number:
            if not re.match(r'^\d{10}$', self.phone_number):
                raise ValidationError({'phone_number': 'Phone number must be 10 digits long'})

        # Postal code validation
        if self.postal_code and not re.match(r'^\d{6}$', self.postal_code):
            raise ValidationError({'postal_code': 'Postal code must be 6 digits long'})

    def save(self, *args, **kwargs):
        self.full_clean()  # Run all validations before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile for {self.user.username}"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

class Wishlist(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wishlists',
        db_index=True
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='wishlists',
        db_index=True
    )
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']
        
    def __str__(self):
        return f"{self.user.username}'s wishlist item: {self.product.name}"
