THE DETs TOOLKIT - COMPLETE SYSTEM README

Version: 2.0.0 | Status: PRODUCTION READY | Date: March 2026

---

EXECUTIVE SUMMARY

The DETs Toolkit is a comprehensive, decoupled School Management System built for the Nigerian K-12 (6-3-3-4) education sector. Following a strict service-selector architecture, the system provides a complete school-in-a-box solution with 10+ fully integrated apps handling everything from admissions to results.

Core Philosophy

· Decoupled Apps: Each app is self-contained with selectors/services/interfaces
· Service-Mediated: Cross-app communication only through service contracts
· No-Customization Rule: All school-specific logic via SiteConfig toggles
· Permission-Based Navigation: Dynamic menus based on user permissions

---

SYSTEM ARCHITECTURE

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

COMPLETED APPS (11 Total)

1. CORECODE - Foundation Layer (100% Complete)

Zero dependencies - the skeleton of the system

Component Status Key Features
Academic Sessions [Complete] Nigerian 6-3-3-4 structure, term management
Student Classes [Complete] Strict Nigerian class levels (NUR1-SS3)
SiteConfig [Complete] The "No-Customization" Rule implementation
SystemLog [Complete] Comprehensive audit trail
Navigation [Complete] Permission-based dynamic menus
RBAC [Complete] Role-based access control
Exceptions [Complete] 15+ custom exception classes
Selectors [Complete] 5 selector classes
Services [Complete] 4 service modules

2. STUDENTS - Core CRM (100% Complete)

The heart of the system - manages all student data

Component Status Key Features
Models [Complete] Student, Guardian, StudentHistory
Selectors [Complete] 3 selector classes with 20+ methods
Services [Complete] 7 service modules
Forms [Complete] 6 form classes with crispy-tailwind
Validators [Complete] 3 validator classes
Exceptions [Complete] 15 exception classes
Views [Complete] 13 view classes
Templates [Complete] 8 templates with Alpine.js
Bulk Operations [Complete] CSV import/export with preview
Search [Complete] Advanced filtering with multiple views

3. STAFFS - Nigerian Staff Management (100% Complete)

Comprehensive staff management for Nigerian schools

Component Status Key Features
Staff Types [Complete] Principal, VP 1&2, Form Masters, Housemasters
Non-Academic [Complete] Security, Cleaners, Kitchen Staff, Drivers
Subject Assignments [Complete] Teaching loads, class teachers, form masters
Duty Assignments [Complete] Club patrons, sports masters, gate duty
Leave Management [Complete] Leave requests with balance tracking
Staff Attendance [Complete] Check-in/out with shift-based lateness
Performance [Complete] Multi-criteria evaluations
Documents [Complete] Contract management, certificates
Views [Complete] 38+ view classes
Selectors [Complete] 9 selector classes
Services [Complete] 4 service modules

4. ADMISSIONS - Gatekeeper (100% Complete)

Complete application and enrollment management

Component Status Key Features
Applications [Complete] Full application lifecycle
Payment Integration [Complete] Paystack with idempotency
Document Upload [Complete] Supporting documents
Review Workflow [Complete] Approve/reject/waitlist
Enrollment Handoff [Complete] Seamless student creation
Public Portal [Complete] Applicant self-service
Webhooks [Complete] Paystack webhook handling
Selectors [Complete] 3 selector classes
Services [Complete] 3 service modules

5. FINANCE - The Ledger (100% Complete)

Complete financial management system

Component Status Key Features
Invoicing [Complete] Single and bulk invoice creation
Payments [Complete] Cash, POS, transfer, Paystack
Partial Payments [Complete] Handle partial payments with balance
Bulk Payments [Complete] Pay multiple invoices at once
Waivers [Complete] Fee waiver request/approval workflow
Receipts [Complete] Print-ready receipts
Reports [Complete] Revenue, outstanding, aging reports
Export [Complete] CSV/Excel export
Selectors [Complete] 4 selector classes
Services [Complete] 4 service modules

6. RESULTS - Academic Records (100% Complete)

Complete result management system

Component Status Key Features
Subjects [Complete] Subject management with Nigerian core subjects
Result Sheets [Complete] Class/term based result sheets
Grade Calculation [Complete] Nigerian WASSCE grading (A1-F9)
Bulk Upload [Complete] CSV import with validation
Approval Workflow [Complete] Draft → Pending → Approved → Published
Report Cards [Complete] Printable report cards
Cumulative Records [Complete] Term-by-term tracking
Position Calculation [Complete] Automatic class positioning
Selectors [Complete] 5 selector classes
Services [Complete] 3 service modules

7. ATTENDANCE - Tracker (100% Complete)

Comprehensive attendance tracking

Component Status Key Features
Daily Registers [Complete] Class-based daily attendance
Multiple Sessions [Complete] Morning, afternoon, full day
QR Code Check-in [Complete] Student QR code scanning
Bulk Marking [Complete] Mark all present/absent
Attendance Reports [Complete] Daily, weekly, monthly, termly
Alerts [Complete] Low attendance notifications
Student Summaries [Complete] Individual attendance records
Selectors [Complete] 5 selector classes
Services [Complete] 3 service modules

8. PARENTS - Parent Portal (100% Complete)

Parent-facing portal with magic link authentication

Component Status Key Features
Magic Link Auth [Complete] Passwordless email login
Multi-Child Dashboard [Complete] View all children at once
Financial Tracking [Complete] Fee balances and payment history
Exam Clearance [Complete] Real-time clearance status
Notifications [Complete] In-app and email notifications
Messaging [Complete] Parent-teacher communication
Results View [Complete] View published results
Attendance View [Complete] View attendance records
Selectors [Complete] 4 selector classes
Services [Complete] 3 service modules

9. NOTIFICATIONS - Multi-Channel System (100% Complete)

Centralized notification system

Component Status Key Features
Multi-Channel [Complete] Email, SMS, Push, In-app
Templates [Complete] Reusable notification templates
User Preferences [Complete] Per-channel, per-type preferences
Bulk Notifications [Complete] Send to groups (all students, all parents)
Scheduled [Complete] Schedule notifications for later
Delivery Logs [Complete] Track delivery status
Retry Logic [Complete] Automatic retry for failures
Selectors [Complete] 5 selector classes
Services [Complete] 2 service modules

10. AUDIT - Immutable Trail (100% Complete)

Comprehensive audit logging system

Component Status Key Features
Automatic Logging [Complete] Signals-based automatic audit
Immutable Records [Complete] Logs cannot be modified
User Tracking [Complete] Who did what, when, from where
Change Tracking [Complete] Before/after values
Retention Policies [Complete] Configurable retention periods
Archiving [Complete] Automatic log archiving
Export [Complete] CSV export for compliance
Selectors [Complete] 2 selector classes
Services [Complete] 1 service module

11. API - RESTful Interface (In Progress)

Centralized API for all apps

Component Status Key Features
Versioning [In Progress] API version 1 in progress
Authentication [In Progress] JWT token authentication
Serializers [Complete] Serializers for all models
Endpoints [In Progress] RESTful endpoints for all resources
Documentation [In Progress] OpenAPI/Swagger docs

---

TECHNICAL SPECIFICATIONS

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

· [Complete] Permission-based access control
· [Complete] CSRF protection
· [Complete] XSS prevention
· [Complete] SQL injection protection
· [Complete] Secure password hashing
· [Complete] Rate limiting
· [Complete] Audit logging

---

ARCHITECTURE HIGHLIGHTS

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
# GOOD - Other app uses selector
from apps.students.selectors import StudentSelector
student_data = StudentSelector.get_by_id(student_id)  # Returns dict

# GOOD - Other app uses service
from apps.students.services import StudentService
student = StudentService.create_from_admission(applicant_data)

# BAD - Direct model import
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

INSTALLATION

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

PROJECT STRUCTURE

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

KEY FEATURES

Nigerian Education Context

· [Complete] 6-3-3-4 education structure enforcement
· [Complete] Nigerian WASSCE grading (A1-F9)
· [Complete] State/LGA fields
· [Complete] Nigerian phone validation
· [Complete] Naira currency formatting

Multi-Tenant Ready

· [Complete] SiteConfig for school-specific settings
· [Complete] No hardcoded values
· [Complete] All customization through admin

Performance Optimized

· [Complete] Selectors with select_related/prefetch_related
· [Complete] Database indexing on all foreign keys
· [Complete] Pagination on all list views
· [Complete] Celery for async tasks
· [Complete] Caching for frequent queries

Security Hardened

· [Complete] No fields = '__all__' in any form
· [Complete] Permission checks on all views
· [Complete] CSRF protection
· [Complete] XSS prevention
· [Complete] SQL injection protection
· [Complete] Immutable audit logs

---

DATABASE SCHEMA HIGHLIGHTS

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

TESTING

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

DEPLOYMENT

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

ROADMAP

Phase 1 - Core Foundation (COMPLETED)

· [Complete] Corecode app
· [Complete] Students app
· [Complete] Staffs app
· [Complete] Admissions app
· [Complete] Finance app

Phase 2 - Academic Modules (COMPLETED)

· [Complete] Results app
· [Complete] Attendance app
· [Complete] Parents portal
· [Complete] Notifications system
· [Complete] Audit system

Phase 3 - Integration & Polish (COMPLETED)

· [Complete] Multi-channel notifications
· [Complete] QR code attendance
· [Complete] Bulk import/export
· [Complete] Advanced reporting
· [Complete] Performance optimization

Phase 4 - Enterprise Features (IN PROGRESS)

· [In Progress] REST API
· [In Progress] Mobile apps
· [In Progress] SMS integration
· [In Progress] Biometric integration
· [In Progress] Multi-school support

---

CONTRIBUTING

1. Follow the service-selector architecture
2. Never use direct model access in views
3. Always use selectors for reads, services for writes
4. Add tests for all new features
5. Update documentation
6. Run pre-commit hooks before committing

---

LICENSE

Proprietary - All rights reserved

---

SUPPORT

· Documentation: /docs/ directory
· Issues: GitHub Issues
· Email: support@detstoolkit.edu.ng

---

ACKNOWLEDGMENTS

Built with the Nigerian education system in mind, incorporating feedback from:

· Nigerian Ministry of Education guidelines
· WAEC/NECO examination standards
· Private school administrators across Nigeria
· Teachers and education professionals

---

© 2026 DETs Toolkit. All rights reserved.