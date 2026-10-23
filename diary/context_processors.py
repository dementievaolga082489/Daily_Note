from .models import Notebook, Reminder, Entry
from django.utils import timezone

def build_notebook_tree(notebooks):
    """Строит древовидную структуру папок."""
    tree = {}
    for nb in notebooks:
        parent_id = nb.parent_id
        if parent_id not in tree:
            tree[parent_id] = []
        tree[parent_id].append(nb)

    for key in tree:
        tree[key].sort(key=lambda x: x.title)

    def assign_children(parent_id=None):
        items = tree.get(parent_id, [])
        for item in items:
            item.children_list = assign_children(item.id)
            item.has_children = len(item.children_list) > 0
        return items

    return assign_children(None)


def sidebar_notebooks(request):
    """Передаёт список дневников (деревом) и напоминаний."""
    if request.user.is_authenticated:
        all_notebooks = list(Notebook.objects.filter(author=request.user))
        tree_notebooks = build_notebook_tree(all_notebooks)

        calendar_reminders = Reminder.objects.filter(
            author=request.user, remind_at__gte=timezone.now()
        ).order_by("remind_at")[:5]

        entry_reminders = Entry.objects.filter(
            author=request.user, reminder_at__gte=timezone.now(), reminder_sent=False
        ).order_by("reminder_at")[:5]

        return {
            "side_notebooks": tree_notebooks,
            "side_calendar_reminders": calendar_reminders,
            "side_entry_reminders": entry_reminders,
            # Флаг, который запоминает, что мы нажали "Свернуть всё"
            "close_all_notebooks": request.GET.get("close_all") == "1",
        }
    return {"side_notebooks": []}