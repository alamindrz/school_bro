from .staff import (
    # Dashboard
    DashboardView,
    
    # Staff CRUD
    StaffListView,
    StaffDetailView,
    StaffCreateView,
    StaffUpdateView,
    StaffDeleteView,
    StaffStatusUpdateView,
    
    # Subject Assignments
    SubjectAssignmentView,
    SubjectAssignmentDeleteView,
    
    # Duty Assignments
    DutyAssignmentView,
    DutyAssignmentDeleteView,  # Now this exists
    
    # Leave Management
    LeaveRequestView,
    LeaveRequestListView,
    LeaveRequestDetailView,
    LeaveRequestApproveView,
    LeaveRequestRejectView,
    LeaveRequestCancelView,
    
    # Attendance
    StaffAttendanceView,
    StaffAttendanceReportView,
    
    # Performance
    PerformanceEvaluationView,
    PerformanceEvaluationDetailView,
    
    # Qualifications
    QualificationCreateView,
    QualificationDeleteView,
    
    # Documents
    DocumentUploadView,
    DocumentDeleteView,
    
    # Export
    ExportStaffView,
)

__all__ = [
    # Dashboard
    'DashboardView',
    
    # Staff CRUD
    'StaffListView',
    'StaffDetailView',
    'StaffCreateView',
    'StaffUpdateView',
    'StaffDeleteView',
    'StaffStatusUpdateView',
    
    # Subject Assignments
    'SubjectAssignmentView',
    'SubjectAssignmentDeleteView',
    
    # Duty Assignments
    'DutyAssignmentView',
    'DutyAssignmentDeleteView',  # Added
    
    # Leave Management
    'LeaveRequestView',
    'LeaveRequestListView',
    'LeaveRequestDetailView',
    'LeaveRequestApproveView',
    'LeaveRequestRejectView',
    'LeaveRequestCancelView',
    
    # Attendance
    'StaffAttendanceView',
    'StaffAttendanceReportView',
    
    # Performance
    'PerformanceEvaluationView',
    'PerformanceEvaluationDetailView',
    
    # Qualifications
    'QualificationCreateView',
    'QualificationDeleteView',
    
    # Documents
    'DocumentUploadView',
    'DocumentDeleteView',
    
    # Export
    'ExportStaffView',
]