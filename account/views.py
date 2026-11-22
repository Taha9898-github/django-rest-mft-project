from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

from .serializers import EmptySerializer, LoginSerializer, RegistrationSerializer


class RegisterView(GenericAPIView):
    """
    Register a new user account.
    Only requires phone, username, and password.
    Returns a token upon successful registration.
    """
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "message": "Account created successfully.",
                    "token": token.key,
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ObtainTokenView(GenericAPIView):
    """
    Authenticate user and return a token.
    Uses Django's authenticate() function for secure validation.
    Returns generic error message to prevent user enumeration.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(
                request=request,
                username=username,
                password=password
            )

            if user is not None:
                token, created = Token.objects.get_or_create(user=user)
                return Response(
                    {"token": token.key},
                    status=status.HTTP_200_OK
                )

            # Generic error message to prevent user enumeration
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class LogoutView(GenericAPIView):
    """
    Logout authenticated user by deleting their token.
    Requires token authentication.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer

    def post(self, request):
        try:
            # Delete the user's token (invalidates it)
            request.user.auth_token.delete()
            return Response(
                {"message": "Logged out successfully."},
                status=status.HTTP_200_OK
            )
        except AttributeError:
            # User doesn't have a token (shouldn't happen with valid token auth)
            return Response(
                {"error": "No active session found."},
                status=status.HTTP_400_BAD_REQUEST
            )
