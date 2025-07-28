# accounts/forms.py
from django import forms
from .models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']  # select editable fields
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': 'readonly'}),  # commonly email readonly if used as username
        }
