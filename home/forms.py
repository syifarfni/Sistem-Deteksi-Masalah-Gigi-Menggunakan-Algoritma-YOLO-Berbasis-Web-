# your_app/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistrasiForm(UserCreationForm):
    first_name = forms.CharField(label="Nama Depan", max_length=150)
    last_name  = forms.CharField(label="Nama Belakang", max_length=150, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
