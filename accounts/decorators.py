from django.shortcuts import redirect

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

from django.core.exceptions import PermissionDenied

def client_required(view_func):
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            raise PermissionDenied

        # Ensure user role is client
        if request.user.role != "client":
            raise PermissionDenied

        # Ensure linked client profile exists
        if not hasattr(request.user, "client_profile"):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper