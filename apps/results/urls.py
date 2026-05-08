from django.urls import path
from .views import staff

app_name = 'results'

urlpatterns = [
    path('', staff.DashboardView.as_view(), name='dashboard'),
    
    # Score entry and viewing
    path('entry/', staff.SheetEntryView.as_view(), name='sheet_entry'),
    path('sheet/<int:pk>/', staff.SheetDetailView.as_view(), name='sheet_detail'),
    path('class-results/', staff.ClassResultView.as_view(), name='class_result'),
    
    # HTMX endpoints
    path('update-score/', staff.ScoreUpdateView.as_view(), name='update_score'),
    
    # Workflow
    path('sheet/<int:pk>/submit/', staff.SubmitSheetView.as_view(), name='submit_sheet'),
    path('sheet/<int:pk>/publish/', staff.PublishSheetView.as_view(), name='publish_sheet'),
]