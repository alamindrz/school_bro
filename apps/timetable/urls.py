# timetable/urls.py

from django.urls import path
from . import views

app_name = 'timetable'

urlpatterns = [
    # ============================================================
    # ADMIN VIEWS - Full page renders
    # ============================================================
    path('', views.TimetableListView.as_view(), name='timetable_list'),
    path('create/', views.TimetableCreateView.as_view(), name='timetable_create'),
    
    path('<int:pk>/', views.TimetableView.as_view(), name='timetable_view'),
    path('<int:pk>/edit/', views.TimetableEditView.as_view(), name='timetable_edit'),
    path('<int:pk>/delete/', views.TimetableDeleteView.as_view(), name='timetable_delete'),
    path('<int:pk>/copy/', views.TimetableCopyView.as_view(), name='timetable_copy'),
    path('<int:pk>/publish/', views.TimetablePublishView.as_view(), name='timetable_publish'),

    # ============================================================
    # HTMX FRAGMENT ENDPOINTS
    # ============================================================
    
    # Slot editing
    path('htmx/slot/<int:slot_id>/edit/', views.SlotEditFormView.as_view(), name='htmx_slot_edit'),
    path('htmx/slot/<int:slot_id>/cell/', views.SlotCellView.as_view(), name='htmx_slot_cell'),
    path('htmx/slot/<int:slot_id>/update/', views.SlotUpdateView.as_view(), name='htmx_slot_update'),
    path('htmx/slot/<int:slot_id>/clear/', views.SlotClearView.as_view(), name='htmx_slot_clear'),
    
    # Teacher subjects
    path('htmx/teacher-subjects/', views.TeacherSubjectsSelectView.as_view(), name='htmx_teacher_subjects'),
    
    # Stats and clashes
    path('htmx/timetable/<int:pk>/stats/', views.TimetableStatsView.as_view(), name='htmx_timetable_stats'),
    path('htmx/timetable/<int:pk>/clashes/', views.ClashListView.as_view(), name='htmx_clash_list'),
    
    # Recommendations
    path('htmx/timetable/<int:pk>/recommendations/', views.RecommendationsView.as_view(), name='htmx_recommendations'),
    path('htmx/timetable/<int:pk>/apply-recommendation/', views.ApplyRecommendationView.as_view(), name='htmx_apply_recommendation'),
    
    # Bulk operations
    path('htmx/timetable/<int:pk>/clear-all/', views.ClearAllView.as_view(), name='htmx_clear_all'),
    
    # ============================================================
    # JSON API ENDPOINTS
    # ============================================================
    path('api/check-clash/', views.ClashCheckView.as_view(), name='api_clash_check'),
    path('api/teacher-availability/', views.TeacherAvailabilityView.as_view(), name='api_teacher_availability'),
    
    # ============================================================
    # STAFF PORTAL VIEWS
    # ============================================================
    path('my-timetable/', views.MyTimetableView.as_view(), name='my_timetable'),
    path('my-timetable/print/', views.MyTimetablePrintView.as_view(), name='my_timetable_print'),
    path('class-timetable/<int:class_id>/', views.ClassTimetableView.as_view(), name='class_timetable'),
    path('class-timetable/<int:class_id>/print/', views.ClassTimetablePrintView.as_view(), name='class_timetable_print'),
    path('portal/api/my-schedule/', views.MyScheduleAPIView.as_view(), name='portal_my_schedule'),
]