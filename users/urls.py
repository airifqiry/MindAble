from django.urls import path
from . import views

urlpatterns = [
    # Public landing / login page
    path('', views.login_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Authenticated pages
    path('home/', views.home, name='home'),
    path('jobs/', views.jobs, name='jobs'),
    path('prep/', views.prep, name='prep'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('basecamp/', views.basecamp, name='basecamp'),

    # API (authenticated)
    path('api/profile/', views.profile_upsert_api, name='api_profile_upsert'),
]