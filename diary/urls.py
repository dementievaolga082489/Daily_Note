from django.urls import path

from . import views

app_name = "diary"

urlpatterns = [
    path("", views.index, name="index"),
    # Entry
    path("entries/", views.EntryListView.as_view(), name="entry_list"),
    path("entries/new/", views.EntryCreateView.as_view(), name="entry_create"),
    path("entries/<int:pk>/", views.EntryDetailView.as_view(), name="entry_detail"),
    path("entries/<int:pk>/edit/", views.EntryUpdateView.as_view(), name="entry_update"),
    path("entries/<int:pk>/delete/", views.EntryDeleteView.as_view(), name="entry_delete"),
    # ★ Маршрут для удаления вложения
    path("attachments/<int:pk>/delete/", views.AttachmentDeleteView.as_view(), name="attachment_delete"),

    # Notebooks (папки/дневники)
    path("notebooks/new/", views.NotebookCreateView.as_view(), name="notebook_create"),
    path("notebooks/<int:pk>/delete/", views.NotebookDeleteView.as_view(), name="notebook_delete"),
    path("notebooks/<int:pk>/edit/", views.NotebookUpdateView.as_view(), name="notebook_update"),
    # Календарь напоминаний
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    path("reminders/new/", views.ReminderCreateView.as_view(), name="reminder_create"),
    path("reminders/<int:pk>/delete/", views.ReminderDeleteView.as_view(), name="reminder_delete"),
    # Записи по дате и по названию
    path("by-date/<str:date>/", views.ByDateView.as_view(), name="by_date"),
    path("by-title/", views.ByTitleView.as_view(), name="by_title"),
]
