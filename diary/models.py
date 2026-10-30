"""Модели приложения diary.

Entry — запись личного дневника.
Reminder — отдельное напоминание для календаря.
Tag — тег для записи.
"""

import datetime
import os

from django.conf import settings
from django.db import models
from django.urls import reverse


class Tag(models.Model):
    """Тег записи (путешествия, мысли, книги, рецепты и т.п.)."""

    name = models.CharField("Название", max_length=50, unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Notebook(models.Model):
    """Дневник (папка) пользователя."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notebooks",
        verbose_name="Автор",
    )
    title = models.CharField("Название", max_length=120)

    # ★ Новое поле: родительская папка
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родительская папка",
        help_text="Оставьте пустым, если это корневая папка.",
    )

    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Дневник"
        verbose_name_plural = "Дневники"
        ordering = ["title"]
        # Уникальность названия теперь проверяем внутри одной родительской папки
        constraints = [
            models.UniqueConstraint(
                fields=["author", "parent", "title"],
                name="unique_notebook_title_per_parent",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Entry(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name="Автор",
    )
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
        verbose_name="Дневник",
    )
    title = models.CharField("Заголовок", blank=True, max_length=200)
    content = models.TextField("Содержание", blank=True)
    date = models.DateField("Дата записи", default=datetime.date.today, help_text="По умолчанию — сегодняшняя дата.")
    tags = models.ManyToManyField(Tag, blank=True, related_name="entries", verbose_name="Теги")
    reminder_at = models.DateTimeField("Напомнить в", null=True, blank=True)
    reminder_sent = models.BooleanField("Напоминание отправлено", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]  # Сначала новые по дате
        verbose_name = "Запись"
        verbose_name_plural = "Записи"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("diary:entry_detail", kwargs={"pk": self.pk})


class Attachment(models.Model):
    """Фото или видео, прикреплённые к записи."""

    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Запись",
    )
    file = models.FileField("Файл", upload_to="attachments/%Y/%m/%d/", help_text="Загрузите фото или видео.")
    is_video = models.BooleanField("Это видео", default=False, help_text="Поставьте галочку, если загружаете видео.")
    is_drawing = models.BooleanField("Это рисунок", default=False)
    is_document = models.BooleanField("Это документ", default=False)
    uploaded_at = models.DateTimeField("Загружено", auto_now_add=True)

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"

    def __str__(self):
        return f"Вложение для {self.entry.title or self.entry.date}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class Reminder(models.Model):
    """Напоминание в личном календаре."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reminders",
        verbose_name="Автор",
        help_text="Пользователь, которому принадлежит напоминание.",
    )
    title = models.CharField(
        "Название",
        max_length=200,
        help_text="Краткое название события.",
    )
    description = models.TextField(
        "Описание",
        blank=True,
        help_text="Дополнительные детали (необязательно).",
    )
    remind_at = models.DateTimeField(
        "Когда напомнить",
        help_text="Дата и время отправки напоминания в Email.",
    )
    sent = models.BooleanField(
        "Отправлено",
        default=False,
        help_text="Флаг ставится Celery-задачей после успешной отправки.",
    )
    created_at = models.DateTimeField(
        "Создано",
        auto_now_add=True,
        help_text="Дата и время создания напоминания.",
    )

    class Meta:
        ordering = ["remind_at"]
        verbose_name = "Напоминание"
        verbose_name_plural = "Напоминания"
        indexes = [
            models.Index(fields=["author", "remind_at"]),
            models.Index(fields=["remind_at", "sent"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} @ {self.remind_at:%d.%m.%Y %H:%M}"

    def get_absolute_url(self) -> str:
        return reverse(
            "diary:by_date",
            kwargs={"date": self.remind_at.date().isoformat()},
        )
