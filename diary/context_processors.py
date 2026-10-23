"""Контекстные процессоры приложения diary."""

from .models import Notebook


def sidebar_notebooks(request):
    """Передаёт список дневников пользователя во все шаблоны (для сайдбара)."""
    if request.user.is_authenticated:
        return {
            "side_notebooks": Notebook.objects.filter(author=request.user),
        }
    return {"side_notebooks": Notebook.objects.none()}