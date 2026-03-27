from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('basecamp/', views.basecamp, name='basecamp'),
    path('passport/step1/', views.passport_step1, name='passport_step1'),
    path('passport/step2/', views.passport_step2, name='passport_step2'),
    path('passport/step3/', views.passport_step3, name='passport_step3'),
    path('passport/step4/', views.passport_step4, name='passport_step4'),
]