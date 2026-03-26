from rest_framework import generics, permissions
from .models import JobFeedback
from .serializers import JobFeedbackSerializer

class JobFeedbackListCreate(generics.ListCreateAPIView):
    serializer_class = JobFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # users only ever see their own feedback
        return JobFeedback.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # automatically attach the logged-in user
        serializer.save(user=self.request.user)


class JobFeedbackDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JobFeedback.objects.filter(user=self.request.user)