"""Админка приложения users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = ("username", "email", "email_verified", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "email_verified")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        ("Дополнительно", {
            "fields": (
                "phone", "avatar", "description",
                "email_verified", "email_verification_token",
            )
        }),
    )

