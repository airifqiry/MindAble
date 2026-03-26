from rest_framework import serializers
from .models import User, WorkplacePassport

class WorkplacePassportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkplacePassport
        # These are the fields from your model that will be "saved"
        fields = ['resume_pdf', 'experience_summary', 'skills', 'success_enablers', 'dealbreakers', 'last_updated']
        read_only_fields = ['last_updated']

class UserSerializer(serializers.ModelSerializer):
    # This nests the passport inside the user data
    passport = WorkplacePassportSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_job_seeker', 'daily_capacity', 'passport']
        extra_kwargs = {'password': {'write_only': True}} # Don't send password back to user!

    def create(self, validated_data):
        # This ensures the password is encrypted in PostgreSQL
        user = User.objects.create_user(**validated_data)
        return user