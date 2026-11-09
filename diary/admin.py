"""Админка приложения diary."""

from django.contrib import admin

from .models import Entry, Reminder, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at", "reminder_at", "reminder_sent")
    list_filter = ("reminder_sent", "tags")
    search_fields = ("title", "content")
    filter_horizontal = ("tags",)
    date_hierarchy = "created_at"


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "remind_at", "sent")
    list_filter = ("sent",)
    search_fields = ("title", "description")
    date_hierarchy = "remind_at"
