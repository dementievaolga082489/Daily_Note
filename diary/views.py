"""Представления приложения diary."""

from datetime import date as date_type

from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import EntryForm, NotebookForm, ReminderForm
from .models import Entry, Notebook, Reminder, Attachment  # ← Добавили Attachment
from .permissions import OwnEntryRequiredMixin
from .services import ensure_daily_notebook


# ─── Вспомогательные функции ──────────────────────────────────────────────


def index(request):
    """Главная страница."""
    return render(request, "diary/index.html", {"today": timezone.localdate()})


# ─── Entry ────────────────────────────────────────────────────────────────
class EntryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список записей текущего пользователя."""

    model = Entry
    template_name = "diary/entry_list.html"
    context_object_name = "entries"
    paginate_by = 10
    permission_required = "diary.view_entry"
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        # Гарантируем, что "Ежедневник" существует при любом заходе
        ensure_daily_notebook(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Entry.objects.filter(author=self.request.user)
            .select_related("notebook")
            .prefetch_related("tags", "attachments")
        )

        notebook_id = self.request.GET.get("notebook", "").strip()
        query = self.request.GET.get("q", "").strip()

        if notebook_id.isdigit():
            # Если есть поисковый запрос, ищем во вложенных папках
            if query:
                from .models import Notebook
                try:
                    current_nb = Notebook.objects.get(pk=int(notebook_id), author=self.request.user)
                except Notebook.DoesNotExist:
                    current_nb = None

                if current_nb:
                    nb_ids = [current_nb.id]
                    children = list(Notebook.objects.filter(author=self.request.user))

                    def get_descendants(parent_id):
                        found = []
                        for child in children:
                            if child.parent_id == parent_id:
                                found.append(child.id)
                                found.extend(get_descendants(child.id))
                        return found

                    nb_ids.extend(get_descendants(current_nb.id))
                    qs = qs.filter(notebook_id__in=nb_ids)
            else:
                # Если поиска нет, показываем ТОЛЬКО записи этой папки
                qs = qs.filter(notebook_id=int(notebook_id))

        # Фильтр по слову
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(content__icontains=query))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        notebooks = Notebook.objects.filter(author=self.request.user)
        current_notebook_id = self.request.GET.get("notebook", "").strip()
        query = self.request.GET.get("q", "").strip()  # Получаем поисковый запрос

        current_notebook = None
        child_notebooks = []

        if current_notebook_id.isdigit():
            current_notebook = notebooks.filter(pk=int(current_notebook_id)).first()
            if current_notebook:
                child_notebooks = Notebook.objects.filter(
                    author=self.request.user,
                    parent=current_notebook
                ).order_by("title")

        ctx["query"] = query
        ctx["notebooks"] = notebooks
        ctx["current_notebook_id"] = current_notebook_id
        ctx["current_notebook"] = current_notebook

        # ★ Передаем подпапки ТОЛЬКО если нет поиска
        if not query:
            ctx["child_notebooks"] = child_notebooks
        else:
            ctx["child_notebooks"] = []

        return ctx

class EntryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание записи."""

    model = Entry
    form_class = EntryForm
    template_name = "diary/entry_form.html"
    permission_required = "diary.add_entry"
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()

        # 1. Дата по умолчанию — сегодня
        initial["date"] = timezone.localdate()

        # 2. Папка по умолчанию — та, из которой перешли, или "Ежедневник"
        ensure_daily_notebook(self.request.user)
        notebook_id = self.request.GET.get("notebook", "").strip()

        if notebook_id.isdigit():
            initial["notebook"] = Notebook.objects.filter(
                author=self.request.user, pk=int(notebook_id)
            ).first()
        else:
            initial["notebook"] = Notebook.objects.filter(
                author=self.request.user, title="Ежедневник"
            ).first()

        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)

        # ★ Обработка загруженных файлов (фото/видео)
        files = self.request.FILES.getlist('attachments')
        for f in files:
            is_video = f.content_type.startswith('video/')
            Attachment.objects.create(
                entry=self.object,
                file=f,
                is_video=is_video
            )

        messages.success(self.request, "Запись создана.")
        return response


class EntryDetailView(OwnEntryRequiredMixin, DetailView):
    model = Entry
    template_name = "diary/entry_detail.html"
    context_object_name = "entry"
    required_permission = "diary.view_entry"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx


class EntryUpdateView(OwnEntryRequiredMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = "diary/entry_form.html"
    required_permission = "diary.change_entry"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.reminder_sent = False
        response = super().form_valid(form)

        # ★ Обработка загруженных файлов (фото/видео) при редактировании
        files = self.request.FILES.getlist('attachments')
        for f in files:
            is_video = f.content_type.startswith('video/')
            Attachment.objects.create(
                entry=self.object,
                file=f,
                is_video=is_video
            )

        messages.success(self.request, "Запись обновлена.")
        return response


class EntryDeleteView(OwnEntryRequiredMixin, DeleteView):
    model = Entry
    template_name = "diary/entry_confirm_delete.html"
    success_url = reverse_lazy("diary:entry_list")
    required_permission = "diary.delete_entry"


# ─── Notebook (папки/дневники) ────────────────────────────────────────────
class NotebookCreateView(LoginRequiredMixin, CreateView):
    """Создание дневника (папки)."""

    model = Notebook
    form_class = NotebookForm
    template_name = "diary/notebook_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["author"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        parent_id = self.request.GET.get("parent", "").strip()
        if parent_id.isdigit():
            parent_obj = Notebook.objects.filter(author=self.request.user, pk=int(parent_id)).first()
            if parent_obj:
                initial["parent"] = parent_obj
        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Дневник создан.")
        return super().form_valid(form)

    def get_success_url(self):
        # Если создали подпапку, переходим в неё. Если корневую — в общий список.
        parent_id = self.request.POST.get("parent", "")
        if parent_id:
            return reverse_lazy("diary:entry_list") + f"?notebook={parent_id}"
        return reverse_lazy("diary:entry_list")

class NotebookDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление дневника (папки). Только автор."""

    model = Notebook
    template_name = "diary/notebook_confirm_delete.html"
    success_url = reverse_lazy("diary:entry_list")

    def test_func(self) -> bool:
        return self.get_object().author == self.request.user

class NotebookUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование (переименование) дневника (папки)."""
    model = Notebook
    form_class = NotebookForm
    template_name = "diary/notebook_form.html" # Используем ту же форму

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["author"] = self.request.user
        return kwargs

    def test_func(self) -> bool:
        return self.get_object().author == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Дневник обновлён.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("diary:entry_list")


# ─── Календарь напоминаний ────────────────────────────────────────────────
class CalendarView(LoginRequiredMixin, View):
    """Календарь напоминаний, сгруппированных по дате."""

    template_name = "diary/calendar.html"

    def get(self, request):
        reminders = Reminder.objects.filter(author=request.user)

        month_param = request.GET.get("month", "").strip()
        if month_param:
            try:
                year, month = map(int, month_param.split("-"))
                reminders = reminders.filter(
                    remind_at__year=year, remind_at__month=month
                )
            except ValueError:
                pass

        grouped: dict = {}
        for r in reminders:
            key = r.remind_at.date()
            grouped.setdefault(key, []).append(r)

        return render(request, self.template_name, {
            "grouped_reminders": grouped,
            "month": month_param,
        })


class ReminderCreateView(LoginRequiredMixin, CreateView):
    """Добавление напоминания в календарь."""

    model = Reminder
    form_class = ReminderForm
    template_name = "diary/reminder_form.html"
    success_url = reverse_lazy("diary:calendar")

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, "Напоминание добавлено.")
        return super().form_valid(form)


class ReminderDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление напоминания. Только автор."""

    model = Reminder
    template_name = "diary/reminder_confirm_delete.html"
    success_url = reverse_lazy("diary:calendar")

    def test_func(self) -> bool:
        return self.get_object().author == self.request.user


# ─── Записи по дате ───────────────────────────────────────────────────────
class ByDateView(LoginRequiredMixin, View):
    """Записи и напоминания за конкретную дату."""

    template_name = "diary/by_date.html"

    def get(self, request, date: str):
        try:
            target = date_type.fromisoformat(date)
        except ValueError:
            messages.error(request, "Некорректная дата.")
            return redirect("diary:entry_list")

        entries = Entry.objects.filter(
            author=request.user, date=target,
        ).select_related("notebook")
        reminders = Reminder.objects.filter(
            author=request.user, remind_at__date=target,
        )

        return render(request, self.template_name, {
            "target_date": target,
            "entries": entries,
            "reminders": reminders,
        })


# ─── Записи по названию ───────────────────────────────────────────────────
class ByTitleView(LoginRequiredMixin, View):
    """Записи и напоминания по названию."""

    template_name = "diary/by_title.html"

    def get(self, request):
        query = request.GET.get("title", "").strip()
        entries = Entry.objects.none()
        reminders = Reminder.objects.none()

        if query:
            entries = Entry.objects.filter(
                author=request.user, title__icontains=query,
            ).select_related("notebook")
            reminders = Reminder.objects.filter(
                author=request.user, title__icontains=query,
            )

        return render(request, self.template_name, {
            "query": query,
            "entries": entries,
            "reminders": reminders,
        })