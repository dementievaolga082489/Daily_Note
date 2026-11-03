"""Представления приложения users."""

import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView

from .forms import (
    UserLoginForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import User


class UserRegistrationView(FormView):
    """Регистрация пользователя с подтверждением email."""

    template_name = "users/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        token = secrets.token_hex(16)
        user.email_verification_token = token
        user.save()

        perms = Permission.objects.filter(content_type__app_label="diary")
        user.user_permissions.add(*perms)

        confirm_url = self.request.build_absolute_uri(reverse("users:verify_email", kwargs={"token": token}))

        send_mail(
            subject="Подтверждение почты",
            message=(
                f"Привет, {user.username}!\n\n"
                f"Перейди по ссылке для подтверждения почты:\n{confirm_url}\n\n"
                f"Если ты не регистрировался — просто проигнорируй письмо."
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
        )

        messages.success(
            self.request,
            "Регистрация успешна. Проверьте почту и подтвердите email.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Проверьте правильность заполнения формы.")
        return super().form_invalid(form)


def verify_email(request, token):
    """Одноразовое подтверждение email по токену."""
    user = User.objects.filter(email_verification_token=token).first()
    if not user:
        raise Http404("Ссылка недействительна или уже использована.")

    user.is_active = True
    user.email_verified = True
    user.email_verification_token = ""
    user.save(
        update_fields=[
            "is_active",
            "email_verified",
            "email_verification_token",
        ]
    )

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Email подтверждён. Добро пожаловать!")
    return redirect("diary:index")


class UserLoginView(LoginView):
    """Вход по email."""

    template_name = "users/login.html"
    authentication_form = UserLoginForm
    redirect_authenticated_user = True


def user_logout_view(request):
    """Выход пользователя."""
    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect("diary:index")


class UserProfileView(LoginRequiredMixin, View):
    """Профиль пользователя: редактирование данных."""

    template_name = "users/profile.html"

    def get(self, request):
        form = UserProfileForm(instance=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлён.")
            return redirect("users:profile")
        return render(request, self.template_name, {"form": form})
