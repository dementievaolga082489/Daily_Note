"""Формы приложения users."""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import TelegramProfile, User


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя (email + username + пароли)."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        help_text="Обязательное поле. Должно быть уникальным.",
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class UserLoginForm(AuthenticationForm):
    """Форма входа по email."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("username")
        if email:
            user = User.objects.filter(email=email).first()
            if user and not user.email_verified:
                raise forms.ValidationError(
                    "Email не подтверждён. Проверьте почту или "
                    "запросите повторную отправку письма."
                )
        return cleaned


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля."""

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name",
            "phone", "description", "avatar",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class TelegramProfileForm(forms.ModelForm):
    """Форма привязки Telegram chat_id."""

    class Meta:
        model = TelegramProfile
        fields = ["chat_id"]
        widgets = {"chat_id": forms.TextInput(attrs={"class": "form-control"})}
        labels = {"chat_id": "Ваш Telegram chat_id"}
        help_texts = {
            "chat_id": "Узнайте свой chat_id через @userinfobot и вставьте сюда.",
        }


class UserAdminCreationForm(UserCreationForm):
    """Форма создания пользователя в админке."""

    class Meta:
        model = User
        fields = ("username", "email")


class UserAdminChangeForm(UserChangeForm):
    """Форма редактирования пользователя в админке."""

    class Meta:
        model = User
        fields = "__all__"