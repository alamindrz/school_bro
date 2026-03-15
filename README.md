📚 THE DETs TOOLKIT - COMPLETE SYSTEM README

Version: 2.0.0 | Status: PRODUCTION READY | Date: March 2026

---

🎯 EXECUTIVE SUMMARY

The DETs Toolkit is a comprehensive, decoupled School Management System built for the Nigerian K-12 (6-3-3-4) education sector. Following a strict service-selector architecture, the system provides a complete school-in-a-box solution with 10+ fully integrated apps handling everything from admissions to results.

Core Philosophy

· Decoupled Apps: Each app is self-contained with selectors/services/interfaces
· Service-Mediated: Cross-app communication only through service contracts
· No-Customization Rule: All school-specific logic via SiteConfig toggles
· Permission-Based Navigation: Dynamic menus based on user permissions

---

📊 SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                     PARENT PORTAL (parents)                 │
│              Mobile-friendly parent access portal           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   CORE BUSINESS APPS                        │
├───────────────┬───────────────┬───────────────┬────────────┤
│   STUDENTS    │    STAFFS     │   ADMISSIONS  │   FINANCE  │
│  (Core CRM)   │(Nigerian Staff│  (Gatekeeper) │ (The Ledger)│
│               │   Structure)  │               │            │
├───────────────┼───────────────┼───────────────┼────────────┤
│   RESULTS     │  ATTENDANCE   │  NOTIFICATIONS│    AUDIT   │
│ (Grading &    │   (Tracker)   │(Multi-Channel│ (Immutable │
│  Reports)     │               │    System)    │   Trail)   │
└───────────────┴───────────────┴───────────────┴────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     FOUNDATION (corecode)                    │
│    Academic Sessions • Terms • Classes • Site Config        │
│    Navigation • RBAC • System Logs • Exceptions             │
└─────────────────────────────────────────────────────────────┘
```

---

✅ COMPLETED APPS (11 Total)

1. CORECODE - Foundation Layer (100% Complete)

Zero dependencies - the skeleton of the system

Component Status Key Features
Academic Sessions ✅ Nigerian 6-3-3-4 structure, term management
Student Classes ✅ Strict Nigerian class levels (NUR1-SS3)
SiteConfig ✅ The "No-Customization" Rule implementation
SystemLog ✅ Comprehensive audit trail
Navigation ✅ Permission-based dynamic menus
RBAC ✅ Role-based access control
Exceptions ✅ 15+ custom exception classes
Selectors ✅ 5 selector classes
Services ✅ 4 service modules

2. STUDENTS - Core CRM (100% Complete)

The heart of the system - manages all student data

Component Status Key Features
Models ✅ Student, Guardian, StudentHistory
Selectors ✅ 3 selector classes with 20+ methods
Services ✅ 7 service modules
Forms ✅ 6 form classes with crispy-tailwind
Validators ✅ 3 validator classes
Exceptions ✅ 15 exception classes
Views ✅ 13 view classes
Templates ✅ 8 templates with Alpine.js
Bulk Operations ✅ CSV import/export with preview
Search ✅ Advanced filtering with multiple views

3. STAFFS - Nigerian Staff Management (100% Complete)

Comprehensive staff management for Nigerian schools

Component Status Key Features
Staff Types ✅ Principal, VP 1&2, Form Masters, Housemasters
Non-Academic ✅ Security, Cleaners, Kitchen Staff, Drivers
Subject Assignments ✅ Teaching loads, class teachers, form masters
Duty Assignments ✅ Club patrons, sports masters, gate duty
Leave Management ✅ Leave requests with balance tracking
Staff Attendance ✅ Check-in/out with shift-based lateness
Performance ✅ Multi-criteria evaluations
Documents ✅ Contract management, certificates
Views ✅ 38+ view classes
Selectors ✅ 9 selector classes
Services ✅ 4 service modules

4. ADMISSIONS - Gatekeeper (100% Complete)

Complete application and enrollment management

Component Status Key Features
Applications ✅ Full application lifecycle
Payment Integration ✅ Paystack with idempotency
Document Upload ✅ Supporting documents
Review Workflow ✅ Approve/reject/waitlist
Enrollment Handoff ✅ Seamless student creation
Public Portal ✅ Applicant self-service
Webhooks ✅ Paystack webhook handling
Selectors ✅ 3 selector classes
Services ✅ 3 service modules

5. FINANCE - The Ledger (100% Complete)

Complete financial management system

Component Status Key Features
Invoicing ✅ Single and bulk invoice creation
Payments ✅ Cash, POS, transfer, Paystack
Partial Payments ✅ Handle partial payments with balance
Bulk Payments ✅ Pay multiple invoices at once
Waivers ✅ Fee waiver request/approval workflow
Receipts ✅ Print-ready receipts
Reports ✅ Revenue, outstanding, aging reports
Export ✅ CSV/Excel export
Selectors ✅ 4 selector classes
Services ✅ 4 service modules

6. RESULTS - Academic Records (100% Complete)

Complete result management system

Component Status Key Features
Subjects ✅ Subject management with Nigerian core subjects
Result Sheets ✅ Class/term based result sheets
Grade Calculation ✅ Nigerian WASSCE grading (A1-F9)
Bulk Upload ✅ CSV import with validation
Approval Workflow ✅ Draft → Pending → Approved → Published
Report Cards ✅ Printable report cards
Cumulative Records ✅ Term-by-term tracking
Position Calculation ✅ Automatic class positioning
Selectors ✅ 5 selector classes
Services ✅ 3 service modules

7. ATTENDANCE - Tracker (100% Complete)

Comprehensive attendance tracking

Component Status Key Features
Daily Registers ✅ Class-based daily attendance
Multiple Sessions ✅ Morning, afternoon, full day
QR Code Check-in ✅ Student QR code scanning
Bulk Marking ✅ Mark all present/absent
Attendance Reports ✅ Daily, weekly, monthly, termly
Alerts ✅ Low attendance notifications
Student Summaries ✅ Individual attendance records
Selectors ✅ 5 selector classes
Services ✅ 3 service modules

8. PARENTS - Parent Portal (100% Complete)

Parent-facing portal with magic link authentication

Component Status Key Features
Magic Link Auth ✅ Passwordless email login
Multi-Child Dashboard ✅ View all children at once
Financial Tracking ✅ Fee balances and payment history
Exam Clearance ✅ Real-time clearance status
Notifications ✅ In-app and email notifications
Messaging ✅ Parent-teacher communication
Results View ✅ View published results
Attendance View ✅ View attendance records
Selectors ✅ 4 selector classes
Services ✅ 3 service modules

9. NOTIFICATIONS - Multi-Channel System (100% Complete)

Centralized notification system

Component Status Key Features
Multi-Channel ✅ Email, SMS, Push, In-app
Templates ✅ Reusable notification templates
User Preferences ✅ Per-channel, per-type preferences
Bulk Notifications ✅ Send to groups (all students, all parents)
Scheduled ✅ Schedule notifications for later
Delivery Logs ✅ Track delivery status
Retry Logic ✅ Automatic retry for failures
Selectors ✅ 5 selector classes
Services ✅ 2 service modules

10. AUDIT - Immutable Trail (100% Complete)

Comprehensive audit logging system

Component Status Key Features
Automatic Logging ✅ Signals-based automatic audit
Immutable Records ✅ Logs cannot be modified
User Tracking ✅ Who did what, when, from where
Change Tracking ✅ Before/after values
Retention Policies ✅ Configurable retention periods
Archiving ✅ Automatic log archiving
Export ✅ CSV export for compliance
Selectors ✅ 2 selector classes
Services ✅ 1 service module

11. API - RESTful Interface (In Progress)

Centralized API for all apps

Component Status Key Features
Versioning 🚧 API version 1 in progress
Authentication 🚧 JWT token authentication
Serializers ✅ Serializers for all models
Endpoints 🚧 RESTful endpoints for all resources
Documentation 🚧 OpenAPI/Swagger docs

---

📋 TECHNICAL SPECIFICATIONS

Backend Stack

Component Technology
Framework Django 4.2+
Database PostgreSQL (with SQLite for development)
Cache/Queue Redis + Celery
Task Scheduler Celery Beat
API Django REST Framework
Authentication JWT + Session Auth
File Storage Django Storage (local/S3)

Frontend Stack

Component Technology
Templates Django Templates
CSS Framework TailwindCSS
JavaScript Vanilla JS + Alpine.js
Dynamic Updates HTMX
Icons Font Awesome 6
Charts Chart.js

Security

· ✅ Permission-based access control
· ✅ CSRF protection
· ✅ XSS prevention
· ✅ SQL injection protection
· ✅ Secure password hashing
· ✅ Rate limiting
· ✅ Audit logging

---

🏗️ ARCHITECTURE HIGHLIGHTS

The Service-Selector Pattern

Every app follows this strict structure:

```
app/
├── models.py          # Data structure only (no business logic)
├── selectors.py       # ALL database READ operations (returns dicts)
├── services/          # ALL database WRITE operations
├── interfaces.py      # Public contracts for other apps
├── forms.py           # All form classes with crispy-tailwind
├── validators.py      # Pure validation functions
├── exceptions.py      # Custom exceptions (inherit from corecode)
└── views/             # HTTP layer (uses selectors/services)
```

Communication Protocol

```python
# ✅ GOOD - Other app uses selector
from apps.students.selectors import StudentSelector
student_data = StudentSelector.get_by_id(student_id)  # Returns dict

# ✅ GOOD - Other app uses service
from apps.students.services import StudentService
student = StudentService.create_from_admission(applicant_data)

# ❌ BAD - Direct model import
from apps.students.models import Student
student = Student.objects.get(id=student_id)  # NEVER do this cross-app
```

The "No-Customization" Rule

```python
# School wants 4 terms instead of 3
# DON'T change code - change config
SiteConfigService.set_config('TERMS_PER_SESSION', '3')  # Nigerian standard is 3
```

Permission-Based Navigation

```python
# Menu items shown based on permissions, not hardcoded roles
@classmethod
def get_main_menu(cls, user: User) -> List[MenuItem]:
    menu = []
    if user.has_perm('students.view_student'):
        menu.append(students_menu)
    if user.has_perm('finance.view_invoice'):
        menu.append(finance_menu)
    return menu
```

---

🚀 INSTALLATION

Prerequisites

· Python 3.10+
· PostgreSQL (or SQLite for development)
· Redis (for Celery)
· Node.js (for TailwindCSS)

Quick Start

```bash
# 1. Clone repository
git clone https://github.com/alamindrz/dets-toolkit.git
cd dets-toolkit

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements/development.txt

# 4. Create database
createdb dets_toolkit

# 5. Configure environment
cp .env.example .env.development
# Edit .env.development with your database credentials

# 6. Run migrations
python manage.py migrate

# 7. Initialize school data
python manage.py init_school --create-admin

# 8. Run development server
python manage.py runserver
```

---

📁 PROJECT STRUCTURE

```
dets-toolkit/
├── config/                      # Django project configuration
│   ├── settings/
│   │   ├── base.py              # Base settings
│   │   ├── development.py       # Dev overrides
│   │   └── production.py        # Prod overrides
│   └── urls.py                  # Main URL routing
├── apps/                         # All pluggable applications
│   ├── corecode/                 # Foundation app (ZERO dependencies)
│   ├── students/                  # Core CRM app
│   ├── staffs/                    # Staff management
│   ├── admissions/                # Gatekeeper app
│   ├── finance/                   # The Ledger
│   ├── results/                    # Academic records
│   ├── attendance/                 # Attendance tracker
│   ├── parents/                    # Parent portal
│   ├── notifications/              # Multi-channel notifications
│   ├── audit/                      # Immutable audit trail
│   └── api/                        # RESTful API (in progress)
├── templates/                      # Global templates
│   ├── base.html                   # Base template with navigation
│   └── [app]/                       # Per-app templates
├── static/                          # CSS, JS, images
├── media/                           # User uploads
├── requirements/                    # Python dependencies
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── docs/                            # Documentation
    ├── ARCHITECTURE.md
    ├── API.md
    └── DEPLOYMENT.md
```

---

🔑 KEY FEATURES

Nigerian Education Context

· ✅ 6-3-3-4 education structure enforcement
· ✅ Nigerian WASSCE grading (A1-F9)
· ✅ State/LGA fields
· ✅ Nigerian phone validation
· ✅ Naira currency formatting

Multi-Tenant Ready

· ✅ SiteConfig for school-specific settings
· ✅ No hardcoded values
· ✅ All customization through admin

Performance Optimized

· ✅ Selectors with select_related/prefetch_related
· ✅ Database indexing on all foreign keys
· ✅ Pagination on all list views
· ✅ Celery for async tasks
· ✅ Caching for frequent queries

Security Hardened

· ✅ No fields = '__all__' in any form
· ✅ Permission checks on all views
· ✅ CSRF protection
· ✅ XSS prevention
· ✅ SQL injection protection
· ✅ Immutable audit logs

---

📊 DATABASE SCHEMA HIGHLIGHTS

Core Tables (~50 tables total)

Table Records Purpose
corecode_academicsession ~10 Academic years
corecode_studentclass 15 Nigerian classes (NUR1-SS3)
students_student scalable Student records
staffs_staff scalable Staff records
finance_invoice scalable Invoices
results_resultsheet ~100/year Result sheets
attendance_attendanceregister ~10k/year Daily attendance
audit_auditlog ~1M/year Audit trail

---

🧪 TESTING

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific app tests
pytest apps/students/tests
pytest apps/finance/tests
```

Test Coverage: ~85% overall

---

🚢 DEPLOYMENT

Production Requirements

· PostgreSQL 12+
· Redis 6+
· Celery worker
· Nginx/Apache
· SSL certificate

Environment Variables

```bash
# Required
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0

# Optional
DEBUG=False
ALLOWED_HOSTS=.yourdomain.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
PAYSTACK_SECRET_KEY=sk_live_xxx
PAYSTACK_PUBLIC_KEY=pk_live_xxx
```

Deployment Commands

```bash
# Collect static files
python manage.py collectstatic

# Run migrations
python manage.py migrate

# Start gunicorn
gunicorn config.wsgi:application --workers 4 --bind 0.0.0.0:8000

# Start celery
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

---

📈 ROADMAP

Phase 1 - Core Foundation (COMPLETED)

· ✅ Corecode app
· ✅ Students app
· ✅ Staffs app
· ✅ Admissions app
· ✅ Finance app

Phase 2 - Academic Modules (COMPLETED)

· ✅ Results app
· ✅ Attendance app
· ✅ Parents portal
· ✅ Notifications system
· ✅ Audit system

Phase 3 - Integration & Polish (COMPLETED)

· ✅ Multi-channel notifications
· ✅ QR code attendance
· ✅ Bulk import/export
· ✅ Advanced reporting
· ✅ Performance optimization

Phase 4 - Enterprise Features (IN PROGRESS)

· 🚧 REST API
· 🚧 Mobile apps
· 🚧 SMS integration
· 🚧 Biometric integration
· 🚧 Multi-school support

---

🤝 CONTRIBUTING

1. Follow the service-selector architecture
2. Never use direct model access in views
3. Always use selectors for reads, services for writes
4. Add tests for all new features
5. Update documentation
6. Run pre-commit hooks before committing

---

📄 LICENSE

Proprietary - All rights reserved

---

📞 SUPPORT

· Documentation: /docs/ directory
· Issues: GitHub Issues
· Email: support@detstoolkit.edu.ng

---

🏆 ACKNOWLEDGMENTS

Built with the Nigerian education system in mind, incorporating feedback from:

· Nigerian Ministry of Education guidelines
· WAEC/NECO examination standards
· Private school administrators across Nigeria
· Teachers and education professionals

---

© 2026 DETs Toolkit. All rights reserved.