"""Формы приложения diary."""

import datetime

from django import forms
from django.forms.widgets import FileInput

from .models import Entry, Notebook, Reminder, Tag  # ★ Добавили импорт Tag


class MultipleFileInput(FileInput):
    """Виджет для загрузки нескольких файлов."""

    allow_multiple_selected = True

    def __init__(self, attrs=None):
        # Убираем 'multiple' из attrs, чтобы Django не ругался
        attrs = attrs or {}
        attrs.pop("multiple", None)
        super().__init__(attrs)
        self.attrs["multiple"] = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


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

    attachments = MultipleFileField(
        required=False,
        label="Добавить файлы (фото, видео, документы)",
        help_text="Можно выбрать сразу несколько файлов (PNG, JPG, MP4, PDF, DOCX и т.д.).",
    )

    tags_input = forms.CharField(
        required=False,
        label="Теги",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите теги через запятую (например: спорт, утро)",
            }
        ),
        help_text="Разделяйте теги запятыми.",
    )

    class Meta:
        model = Entry
        fields = ["date", "title", "content", "notebook", "reminder_at"]  # ★ Убрали "tags" из fields
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "notebook": forms.Select(attrs={"class": "form-select"}),
            "reminder_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }
        labels = {
            "date": "Дата",
            "title": "Заголовок",
            "content": "Содержание",
            "notebook": "Дневник (папка)",
            "reminder_at": "Напоминание (Email)",
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
        self.fields["content"].required = False
        self.fields["notebook"].required = False

        # Показываем в выпадающем списке только дневники текущего пользователя
        if user is not None:
            self.fields["notebook"].queryset = Notebook.objects.filter(author=user)

        self.fields["reminder_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["date"].input_formats = ["%Y-%m-%d"]

        # ★ Если редактируем существующую запись, заполняем поле тегов
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(tag.name for tag in self.instance.tags.all())

    def clean_date(self):
        # Если дата не введена, возвращаем сегодняшнюю
        date = self.cleaned_data.get("date")
        if not date:
            return datetime.date.today()
        return date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()

            # ★ Обрабатываем введенные теги через запятую
            tags_str = self.cleaned_data.get("tags_input", "")
            if tags_str:
                # Разбиваем по запятой, убираем пробелы, создаем или находим теги
                tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
                tags = []
                for name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    tags.append(tag)
                instance.tags.set(tags)
            else:
                # Если поле пустое, очищаем теги (если были)
                instance.tags.clear()

        return instance


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
