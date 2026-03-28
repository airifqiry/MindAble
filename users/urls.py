from django.urls import path
from . import views

urlpatterns = [

    path('', views.login_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('home/', views.home, name='home'),
    path('jobs/', views.jobs, name='jobs'),
    path('prep/', views.prep, name='prep'),
    path('chat/', views.chat, name='chat'),
    path('chat/api/', views.chat_api, name='chat_api'),
    path('chat/history/', views.chat_history, name='chat_history'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('basecamp/', views.basecamp, name='basecamp'),

    path('api/profile/', views.profile_upsert_api, name='api_profile_upsert'),
    path('api/prep/chat/', views.prep_chat_api, name='api_prep_chat'),
]