"""Формы приложения diary."""
import datetime

from django import forms

from .models import Entry, Notebook, Reminder


from django import forms

from .models import Entry, Notebook, Reminder


class NotebookForm(forms.ModelForm):
    """Форма создания дневника (папки)."""

    class Meta:
        model = Notebook
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Название дневника",
            }),
        }
        labels = {"title": "Название"}
        error_messages = {
            "title": {
                "unique": "Дневник с таким названием уже существует.",
            },
        }

    def __init__(self, *args, **kwargs):
        # author передаём из View, чтобы проверить уникальность в рамках пользователя
        self.author = kwargs.pop("author", None)
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Название не может быть пустым.")

        if self.author is not None:
            qs = Notebook.objects.filter(author=self.author, title__iexact=title)
            # при редактировании исключаем самого себя
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "У вас уже есть дневник с таким названием."
                )
        return title

class EntryForm(forms.ModelForm):
    """Форма создания и редактирования записи дневника."""

    class Meta:
        model = Entry
        fields = ["date", "title", "content", "notebook", "reminder_at", "tags"]
        widgets = {
            "date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d"  ),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "notebook": forms.Select(attrs={"class": "form-select"}),
            "reminder_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "tags": forms.CheckboxSelectMultiple(),
        }
        labels = {
            "date": "Дата",
            "title": "Заголовок",
            "content": "Содержание",
            "notebook": "Дневник (папка)",
            "reminder_at": "Напоминание (Telegram)",
            "tags": "Теги",
        }
        help_texts = {
            "reminder_at": "Оставьте пустым, если напоминание не нужно.",
            "notebook": "Можно оставить пустым — запись будет вне папок.",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Делаем поля необязательными в HTML
        self.fields["date"].required = False
        self.fields["title"].required = False
        self.fields["notebook"].required = False

        # Показываем в выпадающем списке только дневники текущего пользователя
        if user is not None:
            self.fields["notebook"].queryset = Notebook.objects.filter(author=user)

        self.fields["reminder_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["date"].input_formats = ["%Y-%m-%d"]

    def clean_date(self):
        # Если дата не введена, возвращаем сегодняшнюю
        date = self.cleaned_data.get("date")
        if not date:
            return datetime.date.today()
        return date


class ReminderForm(forms.ModelForm):
    """Форма создания напоминания в календаре."""

    class Meta:
        model = Reminder
        fields = ["title", "description", "remind_at"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "remind_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        labels = {
            "title": "Название события",
            "description": "Описание",
            "remind_at": "Когда напомнить",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["remind_at"].input_formats = ["%Y-%m-%dT%H:%M"]