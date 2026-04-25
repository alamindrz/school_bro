"""
Staff Portal URLs
"""

from django.urls import path
from .views import portal, auth

app_name = 'staffs'

urlpatterns = [
    # Authentication
    path('login/', auth.StaffLoginView.as_view(), name='portal_login'),
    path('logout/', portal.StaffLogoutView.as_view(), name='portal_logout'),
    
    # Portal pages
    path('dashboard/', portal.StaffDashboardView.as_view(), name='portal_dashboard'),
    path('my-classes/', portal.MyClassesView.as_view(), name='my_classes'),
    path('my-classes/<int:class_id>/', portal.MyStudentsView.as_view(), name='my_students'),
    path('my-classes/<int:class_id>/<int:subject_id>/', portal.MyStudentsView.as_view(), name='my_students_subject'),
    path('profile/', portal.MyProfileView.as_view(), name='portal_profile'),
]