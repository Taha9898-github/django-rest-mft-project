from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


class RegistrationEndpointTests(TestCase):
    """Tests for POST /account/register endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/account/register/'
        self.valid_data = {
            'phone': '09123456789',
            'username': 'testuser',
            'password': 'StrongPassword123'
        }

    def test_successful_registration(self):
        """Test successful user registration with valid data."""
        response = self.client.post(self.register_url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Account created successfully.')
        self.assertTrue(User.objects.filter(username='testuser').exists())

        # Verify user data
        user = User.objects.get(username='testuser')
        self.assertEqual(user.phone, '09123456789')
        self.assertEqual(user.fullname, '')  # fullname not required during registration

    def test_duplicate_username(self):
        """Test registration with existing username."""
        # Create first user
        User.objects.create_user(
            username='testuser',
            phone='09123456789',
            password='StrongPassword123'
        )

        # Try to register with same username
        data = self.valid_data.copy()
        data['phone'] = '09987654321'  # Different phone

        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_duplicate_phone(self):
        """Test registration with existing phone number."""
        # Create first user
        User.objects.create_user(
            username='testuser1',
            phone='09123456789',
            password='StrongPassword123'
        )

        # Try to register with same phone
        data = self.valid_data.copy()
        data['username'] = 'testuser2'  # Different username

        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

    def test_missing_required_fields(self):
        """Test registration with missing required fields."""
        # Missing phone
        response = self.client.post(
            self.register_url,
            {'username': 'testuser', 'password': 'StrongPassword123'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

        # Missing username
        response = self.client.post(
            self.register_url,
            {'phone': '09123456789', 'password': 'StrongPassword123'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

        # Missing password
        response = self.client.post(
            self.register_url,
            {'phone': '09123456789', 'username': 'testuser'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_invalid_phone_format(self):
        """Test registration with invalid phone format."""
        # Phone with letters
        data = self.valid_data.copy()
        data['phone'] = '0912345abc'

        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

    def test_weak_password(self):
        """Test registration with weak password."""
        data = self.valid_data.copy()
        data['password'] = '123'  # Too short

        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_password_not_in_response(self):
        """Test that password is never returned in response."""
        response = self.client.post(self.register_url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)
        self.assertNotIn('password_hash', response.data)

    def test_password_is_hashed(self):
        """Test that password is stored as hash, not plaintext."""
        self.client.post(self.register_url, self.valid_data, format='json')

        user = User.objects.get(username='testuser')
        self.assertNotEqual(user.password, 'StrongPassword123')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$') or
                       user.password.startswith('argon2') or
                       user.password.startswith('$argon2'))


class LoginEndpointTests(TestCase):
    """Tests for POST /account/obtain-token endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.login_url = '/account/obtain-token/'
        self.user = User.objects.create_user(
            username='testuser',
            phone='09123456789',
            password='StrongPassword123'
        )

    def test_correct_credentials(self):
        """Test successful login with correct credentials."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'StrongPassword123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertTrue(len(response.data['token']) > 0)

    def test_incorrect_password(self):
        """Test login with incorrect password."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'WrongPassword123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], 'Invalid credentials.')

    def test_nonexistent_username(self):
        """Test login with non-existent username."""
        response = self.client.post(self.login_url, {
            'username': 'nonexistentuser',
            'password': 'StrongPassword123'
        }, format='json')

        # Should return same error as incorrect password (prevent user enumeration)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], 'Invalid credentials.')

    def test_token_generation(self):
        """Test that token is generated and stored correctly."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'StrongPassword123'
        }, format='json')

        token = response.data['token']
        self.assertTrue(Token.objects.filter(user=self.user, key=token).exists())

    def test_missing_fields(self):
        """Test login with missing fields."""
        # Missing password
        response = self.client.post(self.login_url, {
            'username': 'testuser'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

        # Missing username
        response = self.client.post(self.login_url, {
            'password': 'StrongPassword123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)


class LogoutEndpointTests(TestCase):
    """Tests for POST /account/logout endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.logout_url = '/account/logout/'
        self.user = User.objects.create_user(
            username='testuser',
            phone='09123456789',
            password='StrongPassword123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_successful_logout(self):
        """Test successful logout."""
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logged out successfully.')
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_without_authentication(self):
        """Test logout without authentication token."""
        # Create a new client without authentication
        client = APIClient()
        response = client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_cannot_be_reused_after_logout(self):
        """Test that token is invalid after logout."""
        # Logout
        self.client.post(self.logout_url)

        # Try to use the same token again
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        response = client.post('/account/register/', {
            'phone': '09987654321',
            'username': 'anotheruser',
            'password': 'AnotherPassword123'
        }, format='json')

        # Register endpoint allows anonymous access, but if we try an authenticated endpoint
        # the token should be invalid
        response = client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_only_own_token_deleted(self):
        """Test that only the current user's token is deleted."""
        # Create another user with a token
        another_user = User.objects.create_user(
            username='anotheruser',
            phone='09987654321',
            password='AnotherPassword123'
        )
        another_token = Token.objects.create(user=another_user)

        # Logout the first user
        self.client.post(self.logout_url)

        # Verify only the first user's token was deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertTrue(Token.objects.filter(user=another_user).exists())
