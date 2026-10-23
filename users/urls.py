"""URL-маршруты приложения users."""

from django.urls import path

from .views import (
    MaxSettingsView,
    UserLoginView,
    UserProfileView,
    UserRegistrationView,
    user_logout_view,
    verify_email,
)

app_name = "users"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("logout/", user_logout_view, name="logout"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("max/", MaxSettingsView.as_view(), name="max_settings"),
    path("email-confirm/<str:token>/", verify_email, name="verify_email"),
]