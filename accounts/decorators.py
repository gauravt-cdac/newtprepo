# accounts/decorators.py
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from functools import wraps

def role_required(role):
    def decorator(view_func):
        @wraps(view_func)  
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if request.user.role == role:
                if role == 'seller' and not request.user.is_approved:
                    return HttpResponseForbidden("Your seller account is pending approval.")
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You don't have permission to access this page.")
        return wrapped_view
    return decorator

def admin_required(view_func):
    return role_required('admin')(view_func)

def seller_required(view_func):
    return role_required('seller')(view_func)

def buyer_required(view_func):
    return role_required('buyer')(view_func)
