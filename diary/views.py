"""Представления приложения diary."""

import base64
from datetime import date as date_type

from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.core.files.base import ContentFile
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
from .models import Attachment, Entry, Notebook, Reminder
from .permissions import OwnEntryRequiredMixin
from .services import ensure_daily_notebook


# ─── Вспомогательные функции ──────────────────────────────────────────────

def index(request):
    """Главная страница."""
    context = {"today": timezone.localdate()}

    if request.user.is_authenticated:
        # Получаем последние 3 записи текущего пользователя за текущий месяц
        now = timezone.localdate()
        context["recent_entries"] = Entry.objects.filter(
            author=request.user,
            date__year=now.year,
            date__month=now.month
        ).order_by('-date')[:3]

    return render(request, "diary/index.html", context)
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
        ensure_daily_notebook(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Entry.objects.filter(author=self.request.user)
            .select_related("notebook")
            .prefetch_related("tags", "attachments")
        )

        if self.request.GET.get("all") == "1":
            return qs

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(content__icontains=query))

        tag_query = self.request.GET.get("tag", "").strip()
        if tag_query:
            qs = qs.filter(tags__name__icontains=tag_query)

        date_from = self.request.GET.get("date_from", "").strip()
        date_to = self.request.GET.get("date_to", "").strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        notebook_id = self.request.GET.get("notebook", "").strip()
        if notebook_id.isdigit():
            if query or tag_query or date_from or date_to:
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
                qs = qs.filter(notebook_id=int(notebook_id))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        notebooks = Notebook.objects.filter(author=self.request.user)
        current_notebook_id = self.request.GET.get("notebook", "").strip()

        current_notebook = None
        breadcrumbs = []
        child_notebooks = []

        if current_notebook_id.isdigit():
            current_notebook = notebooks.filter(pk=int(current_notebook_id)).first()
            if current_notebook:
                child_notebooks = Notebook.objects.filter(author=self.request.user, parent=current_notebook).order_by("title")
                breadcrumbs.append(current_notebook)
                parent = current_notebook.parent
                while parent:
                    breadcrumbs.insert(0, parent)
                    parent = parent.parent
        else:
            child_notebooks = Notebook.objects.filter(author=self.request.user, parent__isnull=True).order_by("title")

        ctx["query"] = self.request.GET.get("q", "")
        ctx["tag_query"] = self.request.GET.get("tag", "")
        ctx["date_from"] = self.request.GET.get("date_from", "")
        ctx["date_to"] = self.request.GET.get("date_to", "")
        ctx["notebooks"] = notebooks
        ctx["current_notebook_id"] = current_notebook_id
        ctx["current_notebook"] = current_notebook
        ctx["child_notebooks"] = child_notebooks
        ctx["breadcrumbs"] = breadcrumbs
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
        initial["date"] = timezone.localdate()
        ensure_daily_notebook(self.request.user)
        notebook_id = self.request.GET.get("notebook", "").strip()

        if notebook_id.isdigit():
            initial["notebook"] = Notebook.objects.filter(author=self.request.user, pk=int(notebook_id)).first()
        else:
            initial["notebook"] = Notebook.objects.filter(author=self.request.user, title="Ежедневник").first()

        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)

        for f in self.request.FILES.getlist("attachments"):
            is_video = f.content_type.startswith("video/")
            Attachment.objects.create(entry=self.object, file=f, is_video=is_video)

        drawing_data = self.request.POST.get("drawing_data")
        if drawing_data and drawing_data.startswith("data:image"):
            format, imgstr = drawing_data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"drawing_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
            Attachment.objects.create(entry=self.object, file=data, is_drawing=True)

        messages.success(self.request, "Запись создана.")
        return response

    # ★ Возврат на предыдущую страницу
    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
        return super().get_success_url()


class EntryDetailView(OwnEntryRequiredMixin, DetailView):
    model = Entry
    template_name = "diary/entry_detail.html"
    context_object_name = "entry"
    required_permission = "diary.view_entry"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        breadcrumbs = []
        if self.object.notebook:
            breadcrumbs.append(self.object.notebook)
            parent = self.object.notebook.parent
            while parent:
                breadcrumbs.insert(0, parent)
                parent = parent.parent
        ctx["breadcrumbs"] = breadcrumbs
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

        old_drawing_id = self.request.POST.get("old_drawing_id")
        drawing_data = self.request.POST.get("drawing_data")

        if old_drawing_id and drawing_data:
            Attachment.objects.filter(id=old_drawing_id, entry=self.object).delete()

        for f in self.request.FILES.getlist("attachments"):
            is_video = f.content_type.startswith("video/")
            Attachment.objects.create(entry=self.object, file=f, is_video=is_video)

        if drawing_data and drawing_data.startswith("data:image"):
            format, imgstr = drawing_data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"drawing_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
            Attachment.objects.create(entry=self.object, file=data, is_drawing=True)

        messages.success(self.request, "Запись обновлена.")
        return response

    # ★ Возврат на предыдущую страницу
    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
        return super().get_success_url()


# class EntryDeleteView(OwnEntryRequiredMixin, DeleteView):
#     model = Entry
#     template_name = "diary/entry_confirm_delete.html"
#     required_permission = "diary.delete_entry"
#
#     # ★ Возврат на предыдущую страницу
#     def get_success_url(self):
#         referer = self.request.META.get('HTTP_REFERER')
#         if referer:
#             return referer
#         return reverse_lazy("diary:entry_list")

# class EntryDeleteView(OwnEntryRequiredMixin, DeleteView):
#     model = Entry
#     template_name = "diary/entry_confirm_delete.html"
#     required_permission = "diary.delete_entry"
#
#     def get_object(self, queryset=None):
#         print("=" * 50)
#         print("EntryDeleteView.get_object() вызван")
#         print(f"pk из URL: {self.kwargs.get('pk')}")
#         print(f"user_id: {self.request.user.id}")
#
#         # Вызываем родительский метод (он может взять объект из кэша)
#         obj = super().get_object(queryset)
#
#         print(f"Найден объект: {obj}")
#         if obj:
#             print(f"author_id: {obj.author_id}")
#             print(f"Совпадает ли author_id с user_id? {obj.author_id == self.request.user.id}")
#         print("=" * 50)
#
#         return obj
#
#     def get_success_url(self):
#         referer = self.request.META.get('HTTP_REFERER')
#         if referer:
#             return referer
#         return reverse_lazy("diary:entry_list")

class EntryDeleteView(OwnEntryRequiredMixin, DeleteView):
    model = Entry
    template_name = "diary/entry_confirm_delete.html"
    required_permission = "diary.delete_entry"

    def get_queryset(self):
        # Ищем только среди записей текущего пользователя
        return Entry.objects.filter(author=self.request.user)

    def get_success_url(self):
        # 1. Если в форме было скрытое поле next, возвращаемся туда
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
        # 2. Иначе — в общий список записей
        return reverse_lazy("diary:entry_list")

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

    # ★ Возврат на предыдущую страницу
    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
        parent_id = self.request.POST.get("parent", "")
        if parent_id:
            return reverse_lazy("diary:entry_list") + f"?notebook={parent_id}"
        return reverse_lazy("diary:entry_list")


class NotebookDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление дневника (папки). Только автор."""

    model = Notebook
    template_name = "diary/notebook_confirm_delete.html"

    def test_func(self) -> bool:
        return self.get_object().author == self.request.user

    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
        return reverse_lazy("diary:entry_list")

class NotebookUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование (переименование) дневника (папки)."""

    model = Notebook
    form_class = NotebookForm
    template_name = "diary/notebook_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["author"] = self.request.user
        return kwargs

    def test_func(self) -> bool:
        return self.get_object().author == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Дневник обновлён.")
        return super().form_valid(form)

    # ★ Возврат на предыдущую страницу
    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url:
            return next_url
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
                reminders = reminders.filter(remind_at__year=year, remind_at__month=month)
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

        entries = Entry.objects.filter(author=request.user, date=target).select_related("notebook")
        reminders = Reminder.objects.filter(author=request.user, remind_at__date=target)

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
            entries = Entry.objects.filter(author=request.user, title__icontains=query).select_related("notebook")
            reminders = Reminder.objects.filter(author=request.user, title__icontains=query)

        return render(request, self.template_name, {
            "query": query,
            "entries": entries,
            "reminders": reminders,
        })