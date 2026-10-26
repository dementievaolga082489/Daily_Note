"""Management-команда: создание суперпользователя.

Использование:
    poetry run python manage.py csu
    poetry run python manage.py csu --email boss@site.ru --username boss --password "MyStr0ngPass!"

Идемпотентна: повторный запуск обновляет флаги и пароль, не создаёт дубликат.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Создаёт или обновляет суперпользователя."""

    help = "Создаёт суперпользователя (по умолчанию admin@admin.com / 19AaZz)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@admin.com")
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="19AaZz")

    def handle(self, *args, **options):
        User = get_user_model()

        email = options["email"]
        username = options["username"]
        password = options["password"]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": username},
        )

        # Гарантируем корректные значения в любом случае.
        user.username = username or "admin"
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.email_verified = True
        user.set_password(password)
        user.save()

        status = "✅ создан" if created else "♻️  обновлён"
        self.stdout.write(self.style.SUCCESS(f"{status}: {email} (username={user.username}, password={password})"))
