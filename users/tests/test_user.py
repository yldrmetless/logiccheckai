import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Testler için DRF APIClient instance sağlar."""
    return APIClient()


###########REGISTER TESTS###########


@pytest.mark.django_db
class TestUserRegistration:
    register_url = reverse("register")

    def test_register_user_success(self, api_client):
        """Geçerli verilerle kullanıcı kaydının başarılı olması gerekir."""
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword123",
            "first_name": "Test",
            "last_name": "User",
        }

        response = api_client.post(self.register_url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        assert response.data["username"] == payload["username"]
        assert response.data["email"] == payload["email"]
        assert "id" in response.data
        assert "password" not in response.data

        assert User.objects.filter(username="testuser").exists()

    def test_register_user_existing_email_fails(self, api_client):
        """Aynı e-posta ile kayıt olmaya çalışınca hata dönmeli."""
        User.objects.create_user(
            username="existinguser",
            email="duplicate@example.com",
            password="password123",
        )

        payload = {
            "username": "newuser",
            "email": "duplicate@example.com",
            "password": "newpassword123",
        }

        response = api_client.post(self.register_url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
        assert response.data["email"][0] == "This email is already in use."

    def test_register_user_invalid_password_short(self, api_client):
        """Şifre 8 karakterden kısaysa hata dönmeli."""
        payload = {
            "username": "shortpass",
            "email": "short@example.com",
            "password": "123",
        }

        response = api_client.post(self.register_url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data


#######LOGIN TESTS###########
@pytest.mark.django_db
class TestUserLogin:
    login_url = reverse("login")

    @pytest.fixture
    def active_user(self):
        """Test için hazır bir kullanıcı oluşturur."""
        return User.objects.create_user(
            username="testlogin",
            email="login@example.com",
            password="correct_password123",
            is_active=True,
        )

    def test_login_success_with_username(self, api_client, active_user):
        """Username ile başarılı giriş testi."""
        payload = {"username_or_email": "testlogin", "password": "correct_password123"}
        response = api_client.post(self.login_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        assert "refresh_token" in response.data
        assert "expires_time" in response.data

    def test_login_success_with_email(self, api_client, active_user):
        """Email ile başarılı giriş testi."""
        payload = {
            "username_or_email": "login@example.com",
            "password": "correct_password123",
        }
        response = api_client.post(self.login_url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data

    def test_login_fail_invalid_password(self, api_client, active_user):
        """Yanlış şifre ile giriş başarısız olmalı."""
        payload = {"username_or_email": "testlogin", "password": "wrong_password"}
        response = api_client.post(self.login_url, payload, format="json")

        # 403 yerine 401 bekliyoruz
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "The username/email or password is incorrect."

    def test_login_fail_non_existing_user(self, api_client):
        """Olmayan kullanıcı ile giriş başarısız olmalı."""
        payload = {"username_or_email": "nobody", "password": "some_password"}
        response = api_client.post(self.login_url, payload, format="json")

        # 403 yerine 401 bekliyoruz
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "The username/email or password is incorrect."

    def test_login_fail_inactive_user(self, api_client):
        """Pasif kullanıcı (is_active=False) giriş yapamamalı."""
        User.objects.create_user(
            username="inactiveuser", password="password123", is_active=False
        )
        payload = {"username_or_email": "inactiveuser", "password": "password123"}
        response = api_client.post(self.login_url, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "This user is inactive."


#######MY PROFILE TESTS###########
@pytest.mark.django_db
class TestUserProfile:
    profile_url = reverse("my-profile")

    @pytest.fixture
    def authenticated_user(self, api_client):
        """Test için giriş yapmış bir kullanıcı hazırlar."""
        user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="password123",
            first_name="Metehan",
            last_name="Test",
        )
        api_client.force_authenticate(user=user)
        return user

    def test_get_profile_success(self, api_client, authenticated_user):
        """Giriş yapmış kullanıcı kendi profil bilgilerini alabilmeli."""
        response = api_client.get(self.profile_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == 200

        results = response.data["results"]
        assert results["username"] == authenticated_user.username
        assert results["email"] == authenticated_user.email
        assert results["first_name"] == "Metehan"
        assert results["last_name"] == "Test"

    def test_get_profile_unauthenticated_fails(self, api_client):
        """Giriş yapmamış kullanıcı profile erişememeli (401 dönmeli)."""
        response = api_client.get(self.profile_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
