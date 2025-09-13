from django.urls import path
from .views import SignUpView
from django.contrib.auth import views as auth_views
from .views import DashboardView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("dashboard/",DashboardView.as_view(),name = "dashboard")
]
