"""
Timetable Views Package
Exports all views for the timetable app.
"""

# Admin views (full page renders)
from .admin import (
    TimetableListView,
    TimetableCreateView,
    TimetableEditView,
    TimetableView,
    TimetableDeleteView,
    TimetableCopyView,
    TimetablePublishView,
)

# Portal views (teacher/staff read-only)
from .portal import (
    MyTimetableView,
    MyTimetablePrintView,
    ClassTimetableView,
    ClassTimetablePrintView,
    MyScheduleAPIView,
)

# HTMX fragment views (return HTML partials)
from .htmx import (
    SlotEditFormView,
    SlotCellView,
    SlotUpdateView,
    SlotClearView,
    TeacherSubjectsSelectView,
    TimetableStatsView,
    ClashListView,
    RecommendationsView,
    ApplyRecommendationView,
    ClearAllView,
)

# JSON API views (return JSON)
from .api import (
    ClashCheckView,
    TeacherAvailabilityView,
)

__all__ = [
    # Admin views
    'TimetableListView',
    'TimetableCreateView',
    'TimetableEditView',
    'TimetableView',
    'TimetableDeleteView',
    'TimetableCopyView',
    'TimetablePublishView',
    
    # Portal views
    'MyTimetableView',
    'MyTimetablePrintView',
    'ClassTimetableView',
    'ClassTimetablePrintView',
    'MyScheduleAPIView',
    
    # HTMX fragment views
    'SlotEditFormView',
    'SlotCellView',
    'SlotUpdateView',
    'SlotClearView',
    'TeacherSubjectsSelectView',
    'TimetableStatsView',
    'ClashListView',
    'RecommendationsView',
    'ApplyRecommendationView',
    'ClearAllView',
    
    # JSON API views
    'ClashCheckView',
    'TeacherAvailabilityView',
]