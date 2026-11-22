from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Password is write-only and validated using Django's password validators.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['phone', 'username', 'password']
        extra_kwargs = {
            'username': {
                'min_length': 3,
            },
            'phone': {
                'min_length': 10,
            },
        }

    def validate_phone(self, value):
        """Validate phone number format."""
        # Basic validation: should contain only digits and optionally start with +
        if not value.replace('+', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value

    def validate_username(self, value):
        """Validate username uniqueness (also checked in create, but this provides better error messages)."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def create(self, validated_data):
        """Create a new user with encrypted password."""
        user = User.objects.create_user(
            username=validated_data['username'],
            phone=validated_data['phone'],
            password=validated_data['password']
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login/token acquisition.
    Validates username and password without exposing existence of specific accounts.
    """
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )


class EmptySerializer(serializers.Serializer):
    """Serializer used for endpoints without a request body."""
    pass


class UserResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for user responses.
    Excludes sensitive fields like password.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'phone', 'fullname', 'email']
        read_only_fields = fields
