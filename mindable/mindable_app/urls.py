from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),  # mounts all users urls at root
    path('api-auth/', include('rest_framework.urls')),
    path('api/jobs/', include('jobs.urls')),
    path('api/feedback/', include('feedback.urls')),
]