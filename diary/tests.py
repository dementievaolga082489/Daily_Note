from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Entry, Notebook, Attachment

User = get_user_model()


class DiaryViewsTest(TestCase):
    """Тесты для проверки работы дневника."""

    def setUp(self):
        """Создаем тестового пользователя и клиент для запросов."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )
        # ★ ВЫДАЕМ ПРАВА, ЧТОБЫ ТЕСТЫ НЕ ПАДАЛИ С ОШИБКОЙ 403
        # Проще всего сделать пользователя суперпользователем для тестов
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

        # Или можно выдать конкретные права:
        # perms = Permission.objects.filter(content_type__app_label="diary")
        # self.user.user_permissions.add(*perms)

        self.client = Client()
        self.client.login(email="test@example.com", password="testpassword123")

        # Создаем базовую папку
        self.notebook = Notebook.objects.create(author=self.user, title="Ежедневник")

    def test_entry_create(self):
        """Проверка создания записи."""
        response = self.client.post(reverse("diary:entry_create"), {
            "title": "Тестовая запись",
            "content": "Текст записи",
            "date": "2026-10-27",
            "notebook": self.notebook.id,
        })
        # Должен быть редирект после успешного создания
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Entry.objects.count(), 1)
        self.assertEqual(Entry.objects.first().title, "Тестовая запись")

    def test_entry_delete_and_redirect(self):
        """Проверка удаления записи и редиректа на предыдущую страницу."""
        entry = Entry.objects.create(
            author=self.user,
            title="Удаляемая запись",
            content="Текст",
            notebook=self.notebook
        )
        # Передаем 'next', чтобы проверить возврат
        response = self.client.post(
            reverse("diary:entry_delete", args=[entry.id]),
            {"next": "/entries/?notebook=1"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/entries/?notebook=1")
        self.assertEqual(Entry.objects.count(), 0)

    def test_notebook_create(self):
        """Проверка создания папки."""
        response = self.client.post(reverse("diary:notebook_create"), {
            "title": "Новая папка",
            "parent": self.notebook.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notebook.objects.count(), 2)
        self.assertTrue(Notebook.objects.filter(title="Новая папка").exists())

    def test_attachment_delete(self):
        """Проверка удаления отдельного вложения."""
        entry = Entry.objects.create(
            author=self.user,
            title="Запись с файлом",
            content="Текст",
            notebook=self.notebook
        )
        # Создаем тестовый файл
        test_file = SimpleUploadedFile("test.txt", b"file_content")
        attachment = Attachment.objects.create(entry=entry, file=test_file, is_document=True)

        response = self.client.post(reverse("diary:attachment_delete", args=[attachment.id]))

        # Должен быть редирект на страницу записи
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Attachment.objects.count(), 0)