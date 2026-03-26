from django.urls import path
from .views import JobFeedbackListCreate, JobFeedbackDetail

urlpatterns = [
    path('', JobFeedbackListCreate.as_view()),          # list & create
    path('<int:pk>/', JobFeedbackDetail.as_view()),     # update & delete
]