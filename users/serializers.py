from rest_framework import serializers
from .models import User, WorkplaceProfileSerializer

class UserSerializer(serializers.ModelSerializer):
    profile = WorkplaceProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_job_seeker', 'daily_capacity', 'profile']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user