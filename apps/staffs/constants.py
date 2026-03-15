"""
Staffs App Constants
Pure constants - no dependencies
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class StaffType:
    """Types of staff members - Nigerian School Context"""
    
    # Academic Staff
    TEACHING = 'teaching'
    FORM_MASTER = 'form_master'
    CLASS_TEACHER = 'class_teacher'
    SUBJECT_TEACHER = 'subject_teacher'
    HOD = 'hod'  # Head of Department
    
    # Administrative Staff
    PRINCIPAL = 'principal'
    VICE_PRINCIPAL_1 = 'vice_principal_1'
    VICE_PRINCIPAL_2 = 'vice_principal_2'
    ADMIN_OFFICER = 'admin_officer'
    ADMISSIONS_OFFICER = 'admissions_officer'
    EXAM_OFFICER = 'exam_officer'
    GUIDANCE_COUNSELOR = 'guidance_counselor'
    LIBRARIAN = 'librarian'
    ACCOUNTANT = 'accountant'
    BURSAR = 'bursar'
    SECRETARY = 'secretary'
    
    # Boarding Staff (if boarding school)
    HOSTEL_MASTER = 'hostel_master'  # Male hostel supervisor
    HOSTEL_MISTRESS = 'hostel_mistress'  # Female hostel supervisor
    HOUSEMASTER = 'housemaster'  # Same as hostel master
    KITCHEN_MASTER = 'kitchen_master'
    KITCHEN_STAFF = 'kitchen_staff'
    MATRON = 'matron'
    PATRON = 'patron'
    
    # Co-curricular Staff
    SPORTS_MASTER = 'sports_master'
    GAMES_MASTER = 'games_master'
    CLUBS_MASTER = 'clubs_master'
    CULTURAL_MASTER = 'cultural_master'
    DEBATE_MASTER = 'debate_master'
    JETS_CLUB = 'jets_club'  # Junior Engineers, Technicians and Scientists Club
    
    # Support Staff
    SECURITY = 'security'
    GATE_MAN = 'gate_man'
    CLEANER = 'cleaner'
    GROUNDSKEEPER = 'groundskeeper'
    DRIVER = 'driver'
    MECHANIC = 'mechanic'
    ELECTRICIAN = 'electrician'
    CARPENTER = 'carpenter'
    NURSE = 'nurse'  # School clinic
    DOCTOR = 'doctor'  # Visiting doctor
    CHAPLAIN = 'chaplain'  # For mission schools
    IMAM = 'imam'  # For Islamic schools
    
    # Laboratory Staff
    LAB_ATTENDANT = 'lab_attendant'
    LAB_TECHNICIAN = 'lab_technician'
    ICT_TECHNICIAN = 'ict_technician'
    
    CHOICES = [
        # Academic Staff
        (TEACHING, _('Teaching Staff')),
        (FORM_MASTER, _('Form Master/Mistress')),
        (CLASS_TEACHER, _('Class Teacher')),
        (SUBJECT_TEACHER, _('Subject Teacher')),
        (HOD, _('Head of Department')),
        
        # Administrative Staff
        (PRINCIPAL, _('Principal')),
        (VICE_PRINCIPAL_1, _('Vice Principal 1')),
        (VICE_PRINCIPAL_2, _('Vice Principal 2')),
        (ADMIN_OFFICER, _('Administrative Officer')),
        (ADMISSIONS_OFFICER, _('Admissions Officer')),
        (EXAM_OFFICER, _('Examinations Officer')),
        (GUIDANCE_COUNSELOR, _('Guidance Counselor')),
        (LIBRARIAN, _('Librarian')),
        (ACCOUNTANT, _('Accountant')),
        (BURSAR, _('Bursar')),
        (SECRETARY, _('Secretary')),
        
        # Boarding Staff
        (HOSTEL_MASTER, _('Hostel Master')),
        (HOSTEL_MISTRESS, _('Hostel Mistress')),
        (HOUSEMASTER, _('Housemaster/Housemistress')),
        (KITCHEN_MASTER, _('Kitchen Master')),
        (KITCHEN_STAFF, _('Kitchen Staff')),
        (MATRON, _('Matron')),
        (PATRON, _('Patron')),
        
        # Co-curricular Staff
        (SPORTS_MASTER, _('Sports Master/Mistress')),
        (GAMES_MASTER, _('Games Master')),
        (CLUBS_MASTER, _('Clubs Master')),
        (CULTURAL_MASTER, _('Cultural Master')),
        (DEBATE_MASTER, _('Debate Master')),
        (JETS_CLUB, _('JETS Club Patron')),
        
        # Support Staff
        (SECURITY, _('Security')),
        (GATE_MAN, _('Gate Man')),
        (CLEANER, _('Cleaner')),
        (GROUNDSKEEPER, _('Groundskeeper')),
        (DRIVER, _('Driver')),
        (MECHANIC, _('Mechanic')),
        (ELECTRICIAN, _('Electrician')),
        (CARPENTER, _('Carpenter')),
        (NURSE, _('Nurse')),
        (DOCTOR, _('Doctor')),
        (CHAPLAIN, _('Chaplain')),
        (IMAM, _('Imam')),
        
        # Laboratory Staff
        (LAB_ATTENDANT, _('Laboratory Attendant')),
        (LAB_TECHNICIAN, _('Laboratory Technician')),
        (ICT_TECHNICIAN, _('ICT Technician')),
    ]


class StaffCategory:
    """Broad categories for grouping staff"""
    
    ACADEMIC = 'academic'
    ADMIN = 'administrative'
    BOARDING = 'boarding'
    COCURRICULAR = 'cocurricular'
    SUPPORT = 'support'
    LAB = 'laboratory'
    MEDICAL = 'medical'
    SECURITY = 'security'
    
    CHOICES = [
        (ACADEMIC, _('Academic Staff')),
        (ADMIN, _('Administrative Staff')),
        (BOARDING, _('Boarding Staff')),
        (COCURRICULAR, _('Co-curricular Staff')),
        (SUPPORT, _('Support Staff')),
        (LAB, _('Laboratory Staff')),
        (MEDICAL, _('Medical Staff')),
        (SECURITY, _('Security Staff')),
    ]


# Map staff types to categories
STAFF_CATEGORY_MAP = {
    # Academic
    StaffType.TEACHING: StaffCategory.ACADEMIC,
    StaffType.FORM_MASTER: StaffCategory.ACADEMIC,
    StaffType.CLASS_TEACHER: StaffCategory.ACADEMIC,
    StaffType.SUBJECT_TEACHER: StaffCategory.ACADEMIC,
    StaffType.HOD: StaffCategory.ACADEMIC,
    
    # Administrative
    StaffType.PRINCIPAL: StaffCategory.ADMIN,
    StaffType.VICE_PRINCIPAL_1: StaffCategory.ADMIN,
    StaffType.VICE_PRINCIPAL_2: StaffCategory.ADMIN,
    StaffType.ADMIN_OFFICER: StaffCategory.ADMIN,
    StaffType.ADMISSIONS_OFFICER: StaffCategory.ADMIN,
    StaffType.EXAM_OFFICER: StaffCategory.ADMIN,
    StaffType.GUIDANCE_COUNSELOR: StaffCategory.ADMIN,
    StaffType.LIBRARIAN: StaffCategory.ADMIN,
    StaffType.ACCOUNTANT: StaffCategory.ADMIN,
    StaffType.BURSAR: StaffCategory.ADMIN,
    StaffType.SECRETARY: StaffCategory.ADMIN,
    
    # Boarding
    StaffType.HOSTEL_MASTER: StaffCategory.BOARDING,
    StaffType.HOSTEL_MISTRESS: StaffCategory.BOARDING,
    StaffType.HOUSEMASTER: StaffCategory.BOARDING,
    StaffType.KITCHEN_MASTER: StaffCategory.BOARDING,
    StaffType.KITCHEN_STAFF: StaffCategory.BOARDING,
    StaffType.MATRON: StaffCategory.BOARDING,
    StaffType.PATRON: StaffCategory.BOARDING,
    
    # Co-curricular
    StaffType.SPORTS_MASTER: StaffCategory.COCURRICULAR,
    StaffType.GAMES_MASTER: StaffCategory.COCURRICULAR,
    StaffType.CLUBS_MASTER: StaffCategory.COCURRICULAR,
    StaffType.CULTURAL_MASTER: StaffCategory.COCURRICULAR,
    StaffType.DEBATE_MASTER: StaffCategory.COCURRICULAR,
    StaffType.JETS_CLUB: StaffCategory.COCURRICULAR,
    
    # Support
    StaffType.CLEANER: StaffCategory.SUPPORT,
    StaffType.GROUNDSKEEPER: StaffCategory.SUPPORT,
    StaffType.DRIVER: StaffCategory.SUPPORT,
    StaffType.MECHANIC: StaffCategory.SUPPORT,
    StaffType.ELECTRICIAN: StaffCategory.SUPPORT,
    StaffType.CARPENTER: StaffCategory.SUPPORT,
    
    # Laboratory
    StaffType.LAB_ATTENDANT: StaffCategory.LAB,
    StaffType.LAB_TECHNICIAN: StaffCategory.LAB,
    StaffType.ICT_TECHNICIAN: StaffCategory.LAB,
    
    # Medical
    StaffType.NURSE: StaffCategory.MEDICAL,
    StaffType.DOCTOR: StaffCategory.MEDICAL,
    
    # Security
    StaffType.SECURITY: StaffCategory.SECURITY,
    StaffType.GATE_MAN: StaffCategory.SECURITY,
}


class EmploymentStatus:
    """Employment status"""
    
    ACTIVE = 'active'
    ON_LEAVE = 'on_leave'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'
    RESIGNED = 'resigned'
    RETIRED = 'retired'
    PROBATION = 'probation'
    CONTRACT = 'contract'
    
    CHOICES = [
        (ACTIVE, _('Active')),
        (ON_LEAVE, _('On Leave')),
        (SUSPENDED, _('Suspended')),
        (TERMINATED, _('Terminated')),
        (RESIGNED, _('Resigned')),
        (RETIRED, _('Retired')),
        (PROBATION, _('Probation')),
        (CONTRACT, _('Contract')),
    ]


class EmploymentType:
    """Type of employment"""
    
    PERMANENT = 'permanent'
    CONTRACT = 'contract'
    PART_TIME = 'part_time'
    CASUAL = 'casual'
    INTERN = 'intern'
    VOLUNTEER = 'volunteer'
    VISITING = 'visiting'  # Visiting teachers/doctors
    
    CHOICES = [
        (PERMANENT, _('Permanent')),
        (CONTRACT, _('Contract')),
        (PART_TIME, _('Part-Time')),
        (CASUAL, _('Casual')),
        (INTERN, _('Intern')),
        (VOLUNTEER, _('Volunteer')),
        (VISITING, _('Visiting')),
    ]


class ShiftType:
    """Work shifts - especially for kitchen, security, etc."""
    
    MORNING = 'morning'
    AFTERNOON = 'afternoon'
    EVENING = 'evening'
    NIGHT = 'night'
    ROTATING = 'rotating'
    FIXED = 'fixed'
    
    CHOICES = [
        (MORNING, _('Morning Shift (6am-2pm)')),
        (AFTERNOON, _('Afternoon Shift (2pm-10pm)')),
        (EVENING, _('Evening Shift (4pm-12am)')),
        (NIGHT, _('Night Shift (10pm-6am)')),
        (ROTATING, _('Rotating Shifts')),
        (FIXED, _('Fixed Schedule')),
    ]


class QualificationType:
    """Types of qualifications"""
    
    DEGREE = 'degree'
    DIPLOMA = 'diploma'
    CERTIFICATE = 'certificate'
    MASTERS = 'masters'
    PHD = 'phd'
    PROFESSIONAL = 'professional'
    TRADE = 'trade'  # For artisans
    NCE = 'nce'  # Nigerian Certificate in Education
    PGDE = 'pgde'  # Post Graduate Diploma in Education
    OTHER = 'other'
    
    CHOICES = [
        (DEGREE, _('Bachelor\'s Degree')),
        (MASTERS, _('Master\'s Degree')),
        (PHD, _('PhD/Doctorate')),
        (NCE, _('Nigerian Certificate in Education')),
        (PGDE, _('PGDE')),
        (DIPLOMA, _('Diploma')),
        (CERTIFICATE, _('Certificate')),
        (PROFESSIONAL, _('Professional Certification')),
        (TRADE, _('Trade Test/Apprenticeship')),
        (OTHER, _('Other')),
    ]


class LeaveType:
    """Types of leave"""
    
    ANNUAL = 'annual'
    SICK = 'sick'
    MATERNITY = 'maternity'
    PATERNITY = 'paternity'
    STUDY = 'study'
    UNPAID = 'unpaid'
    COMPASSIONATE = 'compassionate'
    SABBATICAL = 'sabbatical'
    CASUAL = 'casual'  # Casual leave (few hours/days)
    
    CHOICES = [
        (ANNUAL, _('Annual Leave')),
        (SICK, _('Sick Leave')),
        (MATERNITY, _('Maternity Leave')),
        (PATERNITY, _('Paternity Leave')),
        (STUDY, _('Study Leave')),
        (UNPAID, _('Unpaid Leave')),
        (COMPASSIONATE, _('Compassionate Leave')),
        (SABBATICAL, _('Sabbatical')),
        (CASUAL, _('Casual Leave')),
    ]


class LeaveStatus:
    """Leave request status"""
    
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'
    
    CHOICES = [
        (PENDING, _('Pending')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (CANCELLED, _('Cancelled')),
        (COMPLETED, _('Completed')),
    ]


class Gender:
    """Gender options"""
    
    MALE = 'M'
    FEMALE = 'F'
    
    CHOICES = [
        (MALE, _('Male')),
        (FEMALE, _('Female')),
    ]


class MaritalStatus:
    """Marital status options"""
    
    SINGLE = 'single'
    MARRIED = 'married'
    DIVORCED = 'divorced'
    WIDOWED = 'widowed'
    
    CHOICES = [
        (SINGLE, _('Single')),
        (MARRIED, _('Married')),
        (DIVORCED, _('Divorced')),
        (WIDOWED, _('Widowed')),
    ]


class BloodGroup:
    """Blood group for medical records"""
    
    A_POS = 'A+'
    A_NEG = 'A-'
    B_POS = 'B+'
    B_NEG = 'B-'
    O_POS = 'O+'
    O_NEG = 'O-'
    AB_POS = 'AB+'
    AB_NEG = 'AB-'
    
    CHOICES = [
        (A_POS, _('A+')),
        (A_NEG, _('A-')),
        (B_POS, _('B+')),
        (B_NEG, _('B-')),
        (O_POS, _('O+')),
        (O_NEG, _('O-')),
        (AB_POS, _('AB+')),
        (AB_NEG, _('AB-')),
    ]


class DutyPost:
    """Specific duty posts in school"""
    
    # Academic Posts
    FORM_MASTER = 'form_master'
    ASSISTANT_FORM_MASTER = 'assistant_form_master'
    CLASS_TEACHER = 'class_teacher'
    
    # Boarding Posts
    HOUSEMASTER = 'housemaster'
    ASSISTANT_HOUSEMASTER = 'assistant_housemaster'
    DINING_HALL_PREFECT = 'dining_hall_prefect'
    
    # Co-curricular Posts
    SPORTS_COORDINATOR = 'sports_coordinator'
    GAMES_COACH = 'games_coach'
    CLUB_PATRON = 'club_patron'
    CULTURAL_COORDINATOR = 'cultural_coordinator'
    
    # Duty Posts
    MORNING_DEVOTION = 'morning_devotion'
    ASSEMBLY_DUTY = 'assembly_duty'
    GATE_DUTY = 'gate_duty'
    LAB_DUTY = 'lab_duty'
    LIBRARY_DUTY = 'library_duty'
    EXAM_HALL_DUTY = 'exam_hall_duty'
    
    CHOICES = [
        (FORM_MASTER, _('Form Master/Mistress')),
        (ASSISTANT_FORM_MASTER, _('Assistant Form Master/Mistress')),
        (CLASS_TEACHER, _('Class Teacher')),
        (HOUSEMASTER, _('Housemaster/Housemistress')),
        (ASSISTANT_HOUSEMASTER, _('Assistant Housemaster/Housemistress')),
        (DINING_HALL_PREFECT, _('Dining Hall Prefect')),
        (SPORTS_COORDINATOR, _('Sports Coordinator')),
        (GAMES_COACH, _('Games Coach')),
        (CLUB_PATRON, _('Club Patron')),
        (CULTURAL_COORDINATOR, _('Cultural Coordinator')),
        (MORNING_DEVOTION, _('Morning Devotion')),
        (ASSEMBLY_DUTY, _('Assembly Duty')),
        (GATE_DUTY, _('Gate Duty')),
        (LAB_DUTY, _('Laboratory Duty')),
        (LIBRARY_DUTY, _('Library Duty')),
        (EXAM_HALL_DUTY, _('Examination Hall Duty')),
    ]


# Nigerian states for staff records
NIGERIAN_STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
    'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu',
    'FCT - Abuja', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina',
    'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo',
    'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
]