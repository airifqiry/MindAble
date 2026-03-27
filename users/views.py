from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer
from mindable.mindable_app.profile_analyzer import analyze_profile  
from mindable.mindable_app.embeddings import build_user_embeddings   

class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return Response(
                {"message": "Account created successfully!"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Please provide both username and password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return Response(
                {"message": "Login successful!", "redirect": "/basecamp/"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "Invalid credentials. Please try again."},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK
        )