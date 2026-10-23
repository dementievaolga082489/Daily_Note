"""Формы приложения diary."""
import datetime



from django import forms

from .models import Entry, Notebook, Reminder


class NotebookForm(forms.ModelForm):
    class Meta:
        model = Notebook
        fields = ["title", "parent"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название папки"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "title": "Название папки",
            "parent": "Вложить в папку (необязательно)",
        }
        help_texts = {
            "parent": "Оставьте пустым, чтобы создать корневую папку.",
        }

    def __init__(self, *args, **kwargs):
        self.author = kwargs.pop("author", None)
        super().__init__(*args, **kwargs)

        if self.author:
            # Показываем только папки этого пользователя
            qs = Notebook.objects.filter(author=self.author)
            # Если редактируем существующую папку, исключаем её саму и её потомков
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = qs

        self.fields["parent"].required = False

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        parent = self.cleaned_data.get("parent")

        if self.author:
            # Проверяем, нет ли уже папки с таким же названием в этой же родительской папке
            qs = Notebook.objects.filter(author=self.author, title__iexact=title, parent=parent)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("В этой папке уже есть подпапка с таким названием.")
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
            "reminder_at": "Напоминание (Max)",
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