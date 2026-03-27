from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

urlpatterns = [
    # Public landing / login page
    path('', views.login_view, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Authenticated pages
    path('home/', login_required(TemplateView.as_view(template_name='mindable/dashboard.html')), name='home'),
    path('jobs/', login_required(TemplateView.as_view(template_name='mindable/jobs.html')), name='jobs'),
    path('prep/', login_required(TemplateView.as_view(template_name='mindable/prep.html')), name='prep'),
    path('basecamp/', views.basecamp, name='basecamp'),
    path('passport/step1/', views.passport_step1, name='passport_step1'),
    path('passport/step2/', views.passport_step2, name='passport_step2'),
    path('passport/step3/', views.passport_step3, name='passport_step3'),
    path('passport/step4/', views.passport_step4, name='passport_step4'),
]