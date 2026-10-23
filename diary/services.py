"""Сервисные функции приложения diary."""

from .models import Notebook


def ensure_daily_notebook(user):
    """Гарантирует, что у пользователя есть папка «Ежедневник»."""
    if user.is_authenticated:
        Notebook.objects.get_or_create(author=user, title="Ежедневник")