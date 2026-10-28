from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import User


class UserViewsTest(TestCase):
    """Тесты для проверки работы пользователей."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.client = Client()

        # ★ Создаем ContentType и Permission ДО отправки формы
        content_type, _ = ContentType.objects.get_or_create(
            app_label="diary", model="entry"
        )
        self.perm, _ = Permission.objects.get_or_create(
            codename="add_entry",
            content_type=content_type,
            defaults={"name": "Can add entry"}
        )

    def test_user_registration(self):
        """Проверка регистрации: создание пользователя, выдача прав, отправка письма."""
        response = self.client.post(reverse("users:register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })

        # После успешной регистрации должен быть редирект на страницу входа
        self.assertEqual(response.status_code, 302)

        # Проверяем, что пользователь создан, но неактивен
        user = User.objects.filter(email="newuser@example.com").first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active)

        # ★ Проверяем, что права выданы (через user_permissions)
        perms = user.user_permissions.all()
        self.assertTrue(perms.filter(codename="add_entry").exists())

        # Проверяем, что письмо было отправлено (должно быть 1 письмо в "исходящих")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Подтверждение почты", mail.outbox[0].subject)
        self.assertIn("newuser@example.com", mail.outbox[0].to)

    def test_user_login(self):
        """Проверка успешного входа в систему."""
        # Создаем активного пользователя с подтвержденным email
        user = User.objects.create_user(
            username="loginuser",
            email="loginuser@example.com",
            password="StrongPass123!"
        )
        user.is_active = True
        user.email_verified = True
        user.save()

        response = self.client.post(reverse("users:login"), {
            "username": "loginuser@example.com",
            "password": "StrongPass123!",
        })
        # Успешный вход перенаправляет на главную (или на список записей)
        self.assertEqual(response.status_code, 302)

        # Проверяем, что сессия создана (пользователь залогинен)
        self.assertTrue(response.wsgi_request.user.is_authenticated)