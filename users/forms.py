from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


# STAFF REGISTRATION FORM
class UserRegistrationForm(UserCreationForm):

    class Meta:
        model = User

        fields = [
            'username',
            'contact',
            'employee_id',
            'role',
            'password1',
            'password2'
        ]

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),

            'contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),

            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter employee ID'
            }),

            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


# LOGIN FORM
class UserLoginForm(AuthenticationForm):

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )