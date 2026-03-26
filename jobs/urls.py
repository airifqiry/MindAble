"""
Include this in your main urls.py with:
    path('api/jobs/', include('jobs.urls')),
"""

from django.urls import path
from .views import JobDiscoveryHubView, JobDetailView, NotInterestedView

urlpatterns = [
    # GET  /api/jobs/                     → paginated, passport-matched job feed
    path('', JobDiscoveryHubView.as_view(), name='job-list'),

    # GET  /api/jobs/<id>/                → single job, AI-translated detail
    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),

    # POST /api/jobs/<id>/not-interested/ → dismiss job, suppress similar
    path('<int:pk>/not-interested/', NotInterestedView.as_view(), name='job-not-interested'),
]