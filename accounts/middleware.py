from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

class ActiveUserMiddleware:
    """
    Middleware to check if the user is active.
    If a logged-in user becomes inactive, this logs them out and redirects to the login page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
            messages.error(request, "Your account or your firm has been deactivated.")
            return redirect('login')
            
        response = self.get_response(request)
        return response
