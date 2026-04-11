"""
Enrollment Service - Handoff from Admissions to Students
CRITICAL: This is the ONLY place where admissions calls the students app
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any, List
import logging

from ..models import Application
from ..constants import ApplicationStatus
from ..exceptions import (
    EnrollmentError,
    EnrollmentHandoffError,
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
)
from ..interfaces import ApplicantDataContract
from apps.students.services import StudentService, GuardianService
from apps.students.interfaces import StudentDataContract
from apps.corecode.services import SystemLogService
from apps.corecode.models import SystemLog
from apps.corecode.selectors import StudentClassSelector

logger = logging.getLogger(__name__)


class EnrollmentService:
    """
    Handles enrollment of approved applicants into the students app
    This is the CRITICAL handshake between admissions and students
    """
    
    @classmethod
    @transaction.atomic
    def enroll_applicant(cls, application_id: int, enrolled_by_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Enroll an approved applicant as a student
        """
        print(f"=== ENROLLMENT STARTED for application {application_id} ===")
        
        # Lock the application row
        try:
            application = Application.objects.select_for_update().get(id=application_id)
            print(f"Application found: {application.application_number}, status: {application.status}")
        except Application.DoesNotExist:
            raise ApplicationNotFoundError(f"Application {application_id} not found")
        
        # Validate status
        if application.status != ApplicationStatus.APPROVED:
            print(f"Invalid status: {application.status}, expected APPROVED")
            raise InvalidApplicationStatusError(
                from_status=application.status,
                to_status=ApplicationStatus.ENROLLED,
                message="Only approved applications can be enrolled"
            )
        
        # Check if already enrolled
        if application.enrolled_student_id:
            print(f"Already enrolled with student_id: {application.enrolled_student_id}")
            logger.info(f"Application {application.application_number} already enrolled")
            return {
                'success': True,
                'application_id': application.id,
                'student_id': application.enrolled_student_id,
                'already_enrolled': True,
            }
        
        # Prepare data contract for students app
        applicant_data = cls._prepare_student_data_contract(application)
        print(f"Prepared applicant data: {applicant_data}")
        
        try:
            # CRITICAL: Call students app service
            print("Calling StudentService.create_from_admission...")
            student = StudentService.create_from_admission(applicant_data.to_dict())
            print(f"Student created: ID={student.id}, Name={student.get_full_name}, Admission={student.admission_number}")
            from apps.parents.services import PortalSyncService

            PortalSyncService.sync_from_enrollment(
                application=application,
                student=student,
                guardian_info={
                    'first_name': application.guardian_first_name,
                    'last_name': application.guardian_last_name,
                    'email': application.guardian_email,
                    'phone': application.guardian_phone,
                    'address': application.guardian_address,
                    'occupation': application.guardian_occupation,
                    'relationship': application.guardian_relationship,
                }
            )
                        
            # Store the student ID
            application.enrolled_student_id = student.id
            application.enrolled_at = timezone.now()
            application.status = ApplicationStatus.ENROLLED
            application.save(update_fields=[
                'enrolled_student_id', 'enrolled_at', 'status', 'updated_at'
            ])
            print(f"Application updated to ENROLLED")
            
            # Log the enrollment
            SystemLogService.log_action(
                user=enrolled_by_id,
                action=SystemLog.ActionType.PROMOTION,
                app_label=SystemLog.AppLabel.ADMISSIONS,
                model_name='Application',
                object_id=str(application.id),
                object_repr=application.application_number,
                changes={
                    'action': 'ENROLLED',
                    'student_id': student.id,
                    'student_admission': student.admission_number,
                }
            )
            
            logger.info(
                f"Applicant {application.application_number} enrolled as "
                f"student {student.admission_number}"
            )
            
            print(f"=== ENROLLMENT SUCCESS ===")
            
            return {
                'success': True,
                'application_id': application.id,
                'application_number': application.application_number,
                'student_id': student.id,
                'student_admission_number': student.admission_number,
                'student_name': student.get_full_name,
            }
            
        except Exception as e:
            print(f"=== ENROLLMENT FAILED: {e} ===")
            import traceback
            traceback.print_exc()
            logger.error(f"Enrollment failed for {application.application_number}: {e}")
            raise EnrollmentHandoffError(f"Failed to create student record: {str(e)}")


    @classmethod
    def _prepare_student_data_contract(cls, application: Application) -> ApplicantDataContract:
        """
        Prepare data contract for students app
        Maps application fields to StudentDataContract format
        """
        return ApplicantDataContract(
            first_name=application.first_name,
            last_name=application.last_name,
            middle_name=application.middle_name,
            date_of_birth=application.date_of_birth.isoformat(),
            gender=application.gender,
            current_class_id=application.applying_for_class_id,
            email=application.email,
            phone=application.phone,
            address=application.address,
            city=application.city,
            state_of_origin=application.state_of_origin,
            nationality=application.nationality,
            guardian_first_name=application.guardian_first_name,
            guardian_last_name=application.guardian_last_name,
            guardian_relationship=application.guardian_relationship,
            guardian_phone=application.guardian_phone,
            guardian_email=application.guardian_email,
            guardian_address=application.guardian_address,
            guardian_occupation=application.guardian_occupation,
            application_id=application.id,
            application_number=application.application_number,
            enrollment_session_id=application.applying_for_session_id
        )
        
    
    @classmethod
    def _create_guardian_records(cls, application: Application, student_id: int, created_by_id: Optional[int] = None):
        """
        Create guardian records for the newly enrolled student
        """
        try:
            GuardianService.create_guardian(
                student_id=student_id,
                first_name=application.guardian_first_name,
                last_name=application.guardian_last_name,
                relationship=application.guardian_relationship,
                phone=application.guardian_phone,
                email=application.guardian_email or '',
                address=application.guardian_address or application.address,
                occupation=application.guardian_occupation or '',
                is_primary=True,
                is_emergency_contact=True,
                created_by_id=created_by_id
            )
            logger.info(f"Guardian created for student {student_id}")
        except Exception as e:
            logger.error(f"Failed to create guardian for student {student_id}: {e}")
            # Don't fail enrollment if guardian creation fails
            # Log but continue
    
    @classmethod
    def bulk_enroll(cls, application_ids: List[int], enrolled_by_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Bulk enroll multiple approved applicants
        """
        results = {
            'successful': [],
            'failed': [],
        }
        
        for app_id in application_ids:
            try:
                result = cls.enroll_applicant(app_id, enrolled_by_id)
                results['successful'].append({
                    'application_id': app_id,
                    'student_id': result.get('student_id'),
                    'student_admission': result.get('student_admission_number'),
                })
            except Exception as e:
                results['failed'].append({
                    'application_id': app_id,
                    'error': str(e),
                })
        
        logger.info(
            f"Bulk enrollment: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )
        
        return results