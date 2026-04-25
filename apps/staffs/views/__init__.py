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
    SendInviteView,
    
    # Subject Qualifications (formerly Subject Assignments)
    SubjectAssignmentView,
    SubjectAssignmentDeleteView,
    
    # Duty Assignments
    DutyAssignmentView,
    DutyAssignmentDeleteView,
    
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
    PerformanceEvaluationEditView,
    PerformanceEvaluationDeleteView,
    PerformanceEvaluationPrintView,
    PerformanceEvaluationListView,
    
    # Educational Qualifications
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
    'SendInviteView',
    
    # Subject Qualifications
    'SubjectAssignmentView',
    'SubjectAssignmentDeleteView',
    
    # Duty Assignments
    'DutyAssignmentView',
    'DutyAssignmentDeleteView',
    
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
    'PerformanceEvaluationEditView',
    'PerformanceEvaluationDeleteView',
    'PerformanceEvaluationPrintView',
    'PerformanceEvaluationListView',
    
    # Educational Qualifications
    'QualificationCreateView',
    'QualificationDeleteView',
    
    # Documents
    'DocumentUploadView',
    'DocumentDeleteView',
    
    # Export
    'ExportStaffView',
]