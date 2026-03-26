from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from .views import RegisterView, LoginView, LogoutView

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"message": "CSRF cookie set"})

urlpatterns = [
    path('api/csrf/', get_csrf_token, name='csrf'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
]

"""
API REFERENCE FOR FRONTEND DEV
================================

1. GET /api/csrf/
   - Call this FIRST before any POST request
   - No body needed
   - Just fires it once when the page loads

2. POST /api/register/
   - Body: { "username": "...", "email": "...", "password": "..." }
   - Success (201): { "message": "Account created successfully!" }
   - Error (400): { "username": ["This field is required."], ... }

3. POST /api/login/
   - Body: { "username": "...", "password": "..." }
   - Success (200): { "message": "Login successful!", "redirect": "/basecamp/" }
   - Error (400): { "error": "Please provide both username and password." }
   - Error (401): { "error": "Invalid credentials. Please try again." }

4. POST /api/logout/
   - No body needed
   - Must be logged in (send session cookie)
   - Success (200): { "message": "Logged out successfully." }
   - Error (403): user is not authenticated
"""