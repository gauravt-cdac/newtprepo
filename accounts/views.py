# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django import forms
from .models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User  # your custom user model
from .forms import UserProfileForm  # we'll define this form below
from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'role']  # include role for registration
    
    def clean_password2(self):
        pwd1 = self.cleaned_data.get("password1")
        pwd2 = self.cleaned_data.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError("Passwords don't match")
        return pwd2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optional: Immediately login buyers but sellers need approval
            if user.role == 'buyer':
                login(request, user)
                messages.success(request, "Registration successful! You are now logged in.")
                return redirect('home')
            else:
                messages.success(request, "Seller registration received! Await admin approval.")
                return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=user)
        
    return render(request, 'accounts/profile.html', {'form': form})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        if name and email and message:
            subject = f"Contact Us Inquiry from {name}"
            body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
            send_mail(subject, body, settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER])
            messages.success(request, "Thank you for contacting us! We'll get back to you soon.")
        else:
            messages.error(request, "All fields are required.")
    return render(request, 'accounts/contact.html')