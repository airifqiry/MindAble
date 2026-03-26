from rest_framework import serializers
from .models import JobFeedback

class JobFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobFeedback
        fields = ['id', 'job', 'status', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']