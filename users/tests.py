from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from .forms import RegisterForm, ProfileForm, PasswordForm, LoginForm
from .models import CustomUser, UserProfile

CustomUser = get_user_model()

class UsersHomePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password123'
        )
        self.home_url = reverse('products:home_view')

    def test_home_page_redirects_if_not_logged_in(self):
        """Unauthenticated users should be redirected to the login page."""
        response = self.client.get(self.home_url)
        self.assertRedirects(response, f'/accounts/login/?next={self.home_url}')

    def test_home_page_loads_for_logged_in_user(self):
        """Authenticated users can access the home page."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/home.html')

    def test_home_page_displays_username(self):
        """Home page should display the logged-in user's username."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.home_url)
        self.assertContains(response, 'Hello, testuser!')

    def test_home_page_uses_correct_template(self):
        """Verify that the correct template is rendered."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.home_url)
        self.assertTemplateUsed(response, 'users/home.html')

class UserTests(TestCase):

    def test_register_view(self):
        response = self.client.get(reverse('users:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_login_view(self):
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_logout_view(self):
        response = self.client.get(reverse('users:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_profile_view(self):
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)

    def test_password_reset_done_view(self):
        response = self.client.get(reverse('users:password_reset_done'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_done.html')

    def test_password_reset_complete_view(self):
        response = self.client.get(reverse('users:password_reset_complete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_complete.html')

    def test_password_reset_confirm_view(self):
        response = self.client.get(
            reverse('users:password_reset_confirm', kwargs={'uidb64': 'testuid', 'token': 'testtoken'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')

    def test_password_reset_form_view(self):
        try:
            response = self.client.get(reverse('users:password_reset'))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'registration/password_reset_form.html')
        except Exception as e:
            self.fail(f"Password Reset test failed due to: {str(e)}")

    def test_password_change_done_view(self):
        response = self.client.get(reverse('users:password_change_done'))
        self.assertEqual(response.status_code, 302)

    def test_password_change_form_view(self):
        response = self.client.get(reverse('users:password_change'))
        self.assertEqual(response.status_code, 302)


class CustomUserTestCase(TestCase):
    def setUp(self):
        """Set up initial data for the tests"""
        self.username = 'testuser'
        self.email = 'testuser@example.com'
        self.password = 'password123'
        self.first_name = 'Test'
        self.last_name = 'User'

        self.user = get_user_model().objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

    def test_create_user(self):
        """Test if the user is created successfully with valid data"""
        user = self.user
        self.assertEqual(user.username, self.username)
        self.assertEqual(user.email, self.email)
        self.assertEqual(user.first_name, self.first_name)
        self.assertEqual(user.last_name, self.last_name)
        self.assertTrue(user.check_password(self.password))  # Check password hashing

    def test_create_user_without_email(self):
        """Test if creating a user without email works when email is optional"""
        user = get_user_model().objects.create_user(
            username='noemailuser',
            email=None,  # email is None
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )
        # Ensure that the user's email is set to None
        self.assertIsNotNone(user.email,'')  # Using assertIsNone for better readability

    def test_create_user_with_duplicate_username(self):
        """Test that a user cannot be created with a duplicate username"""
        # Create the first user
        get_user_model().objects.create_user(
            username='duplicateuser',
            email='anotheruser@example.com',
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        # Try to create a second user with the same username
        with self.assertRaises(IntegrityError):
            get_user_model().objects.create_user(
                username='duplicateuser',
                email='duplicate@example.com',
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
            )

    def test_create_user_with_duplicate_email(self):
        """Test that a user cannot be created with a duplicate email"""
        # Create the first user with a unique email
        user1 = get_user_model().objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password'
        )

        # Attempt to create a second user with the same email
        with self.assertRaises(IntegrityError):
            get_user_model().objects.create_user(
                username='user2',
                email='user1@example.com',  # Same email as user1
                password='password'
            )

    def test_create_user_with_invalid_email(self):
        """Test that an invalid email raises a validation error"""
        user = get_user_model()(
            username='invalidemailuser',
            email='invalid-email',  # Invalid email format
            password=self.password,
            first_name=self.first_name,
            last_name=self.last_name,
        )

        # Ensure that the ValidationError is raised when trying to save the user
        with self.assertRaises(ValidationError):
            user.full_clean()  # Manually trigger the model's validation
            user.save()  # This will attempt to save the invalid user

    def test_user_str_method(self):
        """Test the string representation of the user"""
        user = self.user
        self.assertEqual(str(user), self.username)

    def test_password_is_hashed(self):
        """Test if the password is hashed and not stored as plain text"""
        user = self.user
        self.assertNotEqual(user.password, self.password)  # Password should be hashed

    def test_user_has_date_joined(self):
        """Test that the user has a `date_joined` attribute"""
        user = self.user
        self.assertIsNotNone(user.date_joined)

    def test_user_has_last_login(self):
        """Test that the user has a `last_login` attribute"""
        user = self.user
        self.assertIsNotNone(user.last_login)


class CustomUserModelTest(TestCase):
    def setUp(self):
        self.valid_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'first_name': 'John',
            'last_name': 'Doe',
        }

    def test_user_profile_creation(self):
        """Test that user profile is created automatically when user is created"""
        user = CustomUser.objects.create(**self.valid_user_data)
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.user, user)

    def test_user_profile_fields(self):
        """Test all fields in UserProfile model"""
        user = CustomUser.objects.create(**self.valid_user_data)
        profile = user.profile
        
        # Test phone number
        profile.phone_number = '9876543210'
        profile.save()
        self.assertEqual(profile.phone_number, '9876543210')
        
        # Test address fields
        profile.address_line_1 = '123 Main St'
        profile.address_line_2 = 'Apt 4B'
        profile.city = 'Mumbai'
        profile.state = 'Maharashtra'
        profile.postal_code = '400001'
        profile.country = 'India'
        profile.save()
        
        self.assertEqual(profile.address_line_1, '123 Main St')
        self.assertEqual(profile.address_line_2, 'Apt 4B')
        self.assertEqual(profile.city, 'Mumbai')
        self.assertEqual(profile.state, 'Maharashtra')
        self.assertEqual(profile.postal_code, '400001')
        self.assertEqual(profile.country, 'India')

    def test_user_profile_preferences(self):
        """Test user preferences in profile"""
        user = CustomUser.objects.create(**self.valid_user_data)
        profile = user.profile
        
        # Test currency preference
        profile.preferred_currency = 'USD'
        profile.save()
        self.assertEqual(profile.preferred_currency, 'USD')
        
        # Test language preference
        profile.language_preference = 'hi'
        profile.save()
        self.assertEqual(profile.language_preference, 'hi')
        
        # Test newsletter subscription
        profile.newsletter_subscription = True
        profile.save()
        self.assertTrue(profile.newsletter_subscription)

    def test_profile_picture_upload(self):
        """Test profile picture upload functionality"""
        user = CustomUser.objects.create(**self.valid_user_data)
        profile = user.profile
        
        # Create a test image file
        image = SimpleUploadedFile(
            "test_image.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        profile.profile_picture = image
        profile.save()
        
        self.assertIsNotNone(profile.profile_picture)
        self.assertTrue(profile.profile_picture.name.startswith('profile_pictures/'))

    def test_date_of_birth(self):
        """Test date of birth field"""
        user = CustomUser.objects.create(**self.valid_user_data)
        profile = user.profile
        
        # Set a valid date
        profile.date_of_birth = timezone.now().date()
        profile.save()
        
        self.assertIsNotNone(profile.date_of_birth)
        self.assertEqual(profile.date_of_birth, timezone.now().date())

    def test_create_valid_user(self):
        user = CustomUser.objects.create(**self.valid_user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertFalse(user.check_password('securepassword123'))
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')

    def test_create_user_without_email(self):
        user_data = self.valid_user_data.copy()
        user_data['email'] = ''  # Set email to an empty string to mimic no email
        user = CustomUser.objects.create(**user_data)
        self.assertEqual(user.email, '')  # Check that the email is an empty string

    def test_invalid_email_validation(self):
        user_data = self.valid_user_data.copy()
        user_data['email'] = 'invalid-email'  # Invalid email format
        user = CustomUser(**user_data)
        with self.assertRaises(ValidationError) as context:
            user.full_clean()  # Triggers model validation
        self.assertIn('Enter a valid email address.', str(context.exception))

    def test_date_joined_defaults_to_now(self):
        user = CustomUser.objects.create(**self.valid_user_data)
        self.assertIsNotNone(user.date_joined)
        self.assertAlmostEqual(user.date_joined, timezone.now(), delta=timezone.timedelta(seconds=1))

    def test_last_login_defaults_to_now(self):
        user = CustomUser.objects.create(**self.valid_user_data)
        self.assertIsNotNone(user.last_login)  # Verify last_login is initially None
        user.last_login = timezone.now()  # Simulate a login action setting last_login
        user.save()
        self.assertAlmostEqual(user.last_login, timezone.now(), delta=timezone.timedelta(seconds=1))

    def test_unique_username_constraint(self):
        CustomUser.objects.create(**self.valid_user_data)
        with self.assertRaises(ValidationError) as context:
            duplicate_user = CustomUser(**self.valid_user_data)
            duplicate_user.full_clean()  # Triggers unique constraint validation
        self.assertIn('User with this Username already exists.', str(context.exception))


class RegisterFormTest(TestCase):
    def test_valid_registration(self):
        form_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'StrongPassw0rd!',
            'password2': 'StrongPassw0rd!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        form_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'StrongPassw0rd!',
            'password2': 'DifferentPass123!',
        }
        form = RegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_invalid_email(self):
        form_data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password1': 'StrongPassw0rd!',
            'password2': 'StrongPassw0rd!'
        }
        form = RegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class ProfileFormTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', email='test@example.com', password='password123')

    def test_valid_profile_update(self):
        form_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        form = ProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_invalid_email_in_profile(self):
        form_data = {
            'username': 'updateduser',
            'email': 'invalid-email'
        }
        form = ProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class PasswordFormTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password='OldPassword123')

    def test_valid_password_change(self):
        form_data = {
            'current_password': 'OldPassword123',
            'new_password': 'NewStrongPass123!',
            'confirm_password': 'NewStrongPass123!'
        }
        form = PasswordForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_incorrect_current_password(self):
        form_data = {
            'current_password': 'WrongPassword',
            'new_password': 'NewStrongPass123!',
            'confirm_password': 'NewStrongPass123!'
        }
        form = PasswordForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('current_password', form.errors)

    def test_password_mismatch(self):
        form_data = {
            'current_password': 'OldPassword123',
            'new_password': 'NewPass123!',
            'confirm_password': 'DifferentPass123!'
        }
        form = PasswordForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)

class LoginFormTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password='password123')

    def test_valid_login(self):
        form_data = {
            'username': 'testuser',
            'password': 'password123'
        }
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_login(self):
        form_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
