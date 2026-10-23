"""Модели приложения users."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель пользователя проекта."""

    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Введите свой Email.",
    )

    email_verified = models.BooleanField(
        default=False,
        verbose_name="Email подтверждён",
    )
    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Токен подтверждения email",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Телефон",
        help_text="Введите номер телефона.",
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        verbose_name="Аватар",
        help_text="Загрузите изображение профиля. Необязательно.",
    )
    description = models.TextField(
        blank=True,
        max_length=500,
        verbose_name="О себе",
        help_text="Короткое описание профиля, до 500 символов.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.username

    @property
    def full_name(self) -> str:
        return self.get_full_name() or self.username


class TelegramProfile(models.Model):
    """Привязка пользователя к Telegram chat_id.

    Создаётся явно в представлениях (`get_or_create`) — без сигналов.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="telegram_profile",
        verbose_name="Пользователь",
        help_text="Владелец Telegram-профиля.",
    )
    chat_id = models.CharField(
        "Telegram chat_id",
        max_length=64,
        blank=True,
        help_text="Узнать можно через бота @userinfobot. Пустое значение — "
                  "напоминания не отправляются.",
    )

    class Meta:
        verbose_name = "Telegram-профиль"
        verbose_name_plural = "Telegram-профили"

    def __str__(self) -> str:
        return f"{self.user.username} → {self.chat_id or 'не привязан'}"