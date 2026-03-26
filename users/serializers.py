from rest_framework import serializers
from .models import User, WorkplaceProfile

class WorkplaceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkplaceProfile
        fields = ['resume_pdf', 'experience_summary', 'skills', 'success_enablers', 'dealbreakers', 'mental_disability', 'last_updated']
        read_only_fields = ['last_updated']

class UserSerializer(serializers.ModelSerializer):
    profile = WorkplaceProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_job_seeker', 'daily_capacity', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user