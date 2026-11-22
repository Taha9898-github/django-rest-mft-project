from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Adds fullname and phone fields while maintaining compatibility
    with Django's built-in authentication system.
    """
    fullname = models.CharField(
        max_length=50,
        help_text="User's full name"
    )
    phone = models.CharField(
        max_length=12,
        unique=True,
        help_text="User's phone number"
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return self.username
