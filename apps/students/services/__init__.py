"""
Student Services - Business Logic Layer
All student write operations go through these services
"""

from .student import StudentService
from .guardian import GuardianService
from .promotion import PromotionService
from .history import StudentHistoryService
from .admission_number import AdmissionNumberService
from .user_integration import StudentUserService
from .bulk_operations import BulkStudentService  # For future implementation

__all__ = [
    # Core Student Services
    'StudentService',
    'GuardianService',
    'PromotionService',
    'StudentHistoryService',
    
    # Supporting Services
    'AdmissionNumberService',
    'StudentUserService',
    'BulkStudentService',
]