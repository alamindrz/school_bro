"""
Main URL Configuration

Each app is responsible for its own URL definitions.
All app URLs must be registered here with proper namespaces.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Authentication
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    # Core / Dashboard
    path("", include("apps.corecode.urls")),

    # Domain Apps (Namespaced)
    path("students/", include("apps.students.urls", namespace="students")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("staffs/", include("apps.staffs.urls", namespace="staffs")),
    path("admissions/", include("apps.admissions.urls", namespace="admissions")),
    path("finance/", include("apps.finance.urls", namespace="finance")),
    path("results/", include("apps.results.urls", namespace="results")),
    path("attendance/", include("apps.attendance.urls", namespace="attendance")),
]


# Static & Media (Development Only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)