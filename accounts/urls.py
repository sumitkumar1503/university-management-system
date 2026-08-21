from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.UMSLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("profile/", views.profile, name="profile"),
]
