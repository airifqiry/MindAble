from django.urls import path
from .views import JobDiscoveryHubView, JobDetailView, NotInterestedView

urlpatterns = [
    
    path('', JobDiscoveryHubView.as_view(), name='job-list'),

    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),

    path('<int:pk>/not-interested/', NotInterestedView.as_view(), name='job-not-interested'),
]