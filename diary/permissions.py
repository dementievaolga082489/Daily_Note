"""Миксины прав доступа для приложения diary."""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class OwnEntryRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Доступ только к своим записям + проверка права."""

    required_permission: str = ""
    raise_exception = True

    def get_permission_required(self):
        return (self.required_permission,)

    def has_permission(self) -> bool:
        return (
            super().has_permission()
            and self.get_object().author == self.request.user
        )