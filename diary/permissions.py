"""Миксины прав доступа для приложения diary."""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied


class OwnEntryRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Доступ только к своим записям + проверка права."""

    required_permission: str = ""
    raise_exception = True

    def get_permission_required(self):
        return (self.required_permission,)

    def has_permission(self) -> bool:
        # Проверяем только общие права, без get_object()
        return super().has_permission()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user:
            raise PermissionDenied("Вы не можете управлять чужой записью.")
        return obj