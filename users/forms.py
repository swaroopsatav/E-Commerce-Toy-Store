# forms.py
from django import forms
from .models import CustomUser
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import password_validation
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from users.models import UserProfile

class RegisterForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_line_1 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    state = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'password1',
            'password2',
            'first_name',
            'last_name',
            'phone_number',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'postal_code',
            'country'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create profile automatically
            profile = UserProfile.objects.create(
                user=user,
                phone_number=self.cleaned_data['phone_number'],
                address_line_1=self.cleaned_data['address_line_1'],
                address_line_2=self.cleaned_data['address_line_2'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
                postal_code=self.cleaned_data['postal_code'],
                country=self.cleaned_data['country']
            )
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError:
                raise forms.ValidationError('Enter a valid email address.')
        return email

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'phone_number',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'postal_code',
            'country',
            'date_of_birth',
            'profile_picture',
            'preferred_currency',
            'language_preference',
            'newsletter_subscription'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'preferred_currency': forms.Select(attrs={'class': 'form-control'}),
            'language_preference': forms.Select(attrs={'class': 'form-control'}),
            'newsletter_subscription': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'phone_number': 'Phone Number',
            'address_line_1': 'Address Line 1',
            'address_line_2': 'Address Line 2',
            'city': 'City',
            'state': 'State/Province',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'date_of_birth': 'Date of Birth',
            'profile_picture': 'Profile Picture',
            'preferred_currency': 'Preferred Currency',
            'language_preference': 'Language Preference',
            'newsletter_subscription': 'Subscribe to Newsletter'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['phone_number'].initial = profile.phone_number
            self.fields['address_line_1'].initial = profile.address_line_1
            self.fields['address_line_2'].initial = profile.address_line_2
            self.fields['city'].initial = profile.city
            self.fields['state'].initial = profile.state
            self.fields['postal_code'].initial = profile.postal_code
            self.fields['country'].initial = profile.country
            self.fields['date_of_birth'].initial = profile.date_of_birth
            self.fields['preferred_currency'].initial = profile.preferred_currency
            self.fields['language_preference'].initial = profile.language_preference
            self.fields['newsletter_subscription'].initial = profile.newsletter_subscription

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not re.match(r'^\d{10}$', phone_number):
            raise forms.ValidationError('Phone number must be 10 digits long')
        return phone_number

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code and not re.match(r'^\d{6}$', postal_code):
            raise forms.ValidationError('Postal code must be 6 digits long')
        return postal_code

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data['phone_number']
            profile.address_line_1 = self.cleaned_data['address_line_1']
            profile.address_line_2 = self.cleaned_data['address_line_2']
            profile.city = self.cleaned_data['city']
            profile.state = self.cleaned_data['state']
            profile.postal_code = self.cleaned_data['postal_code']
            profile.country = self.cleaned_data['country']
            profile.date_of_birth = self.cleaned_data['date_of_birth']
            profile.preferred_currency = self.cleaned_data['preferred_currency']
            profile.language_preference = self.cleaned_data['language_preference']
            profile.newsletter_subscription = self.cleaned_data['newsletter_subscription']
            profile.save()
        return user

class PasswordForm(forms.ModelForm):
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = []  # No model fields needed for password change

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if self.user and not self.user.check_password(current_password):
            raise forms.ValidationError('Current password is incorrect.')
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'The new passwords do not match.')

        if new_password:
            password_validation.validate_password(new_password, self.user)

        return cleaned_data

class LoginForm(forms.Form):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError('Invalid username or password.')

        return cleaned_data

