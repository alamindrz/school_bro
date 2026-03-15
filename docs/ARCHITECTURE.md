```markdown
# DETs Toolkit Architecture Guide

## Core Architecture Principles

### 1. App Independence
Every app is a self-contained, pluggable module. No circular dependencies.
- **Corecode**: Zero dependencies - foundation of everything
- **Students**: Depends ONLY on corecode
- **Admissions**: Depends on corecode + students (via services only)
- **Finance**: Depends on corecode + students (via services only)
- **Results**: Depends on corecode + students (via services only)

### 2. Service-Mediated Communication
Apps NEVER import each other's models directly. All cross-app communication happens through:
- **Selectors** (READ operations) - Return dictionaries, not model instances
- **Services** (WRITE operations) - Accept dictionaries, not model instances
- **Interfaces** (Contracts) - Define the public API

### 3. The "No-Customization" Rule
All school-specific requirements become toggles in `corecode.SiteConfig`. 
If it can't be configured, the answer is "No".

### 4. Audit Trail
Every sensitive operation (grade changes, payments, status changes) is logged in `corecode.SystemLog`.
Who, What, When, Where - immutable record.

## Directory Structure Standard
```

apps/[app_name]/
├── init.py
├── admin.py              # Django admin configuration
├── apps.py              # App configuration
├── constants.py         # Pure constants, no dependencies
├── interfaces.py        # PUBLIC contracts for other apps
├── models.py           # Data models (own data only)
├── selectors.py        # READ operations (return dicts)
├── services/
│   ├── init.py
│   └── actions.py      # WRITE operations
├── tasks/
│   ├── init.py
│   └── async_tasks.py  # Celery tasks
├── views/
│   ├── init.py
│   ├── public.py       # Unauthenticated views
│   └── staff.py        # Authenticated staff views
├── templates/
│   └── [app_name]/
│       ├── components/ # Reusable UI components
│       └── pages/     # Full page templates
└── tests/
├── init.py
├── test_models.py
├── test_selectors.py
├── test_services.py
└── test_views.py

```

## Communication Protocol

### READ Operations (Cross-App)
```python
# GOOD - Other app uses selector
from apps.students.selectors import StudentSelector

student_data = StudentSelector.get_by_id(student_id)
# Returns DICT, not model instance

# BAD - Direct model import
from apps.students.models import Student

student = Student.objects.get(id=student_id)  # NEVER do this cross-app
```

WRITE Operations (Cross-App)

```python
# GOOD - Other app uses service
from apps.students.services import StudentService

student = StudentService.create_from_admission(applicant_data)

# BAD - Direct model creation
from apps.students.models import Student

Student.objects.create(...)  # NEVER do this cross-app
```

Permission-Based Navigation

No hardcoded roles. Navigation builds dynamically based on user.has_perm().

Defining Permissions

```python
# In each app's models.py or permissions.py
class Meta:
    permissions = [
        ("can_verify_payment", "Can verify payments"),
        ("can_bulk_upload_results", "Can bulk upload results"),
        ("can_promote_students", "Can promote students"),
    ]
```

Dynamic Menu Building

```python
# corecode/navigation/menu.py
def get_menu_for_user(user):
    menu_items = []
    
    if user.has_perm('students.view_student'):
        menu_items.append({'label': 'Students', 'url': reverse('students:list')})
    
    if user.has_perm('finance.can_verify_payment'):
        menu_items.append({'label': 'Finance', 'url': reverse('finance:dashboard')})
    
    return menu_items
```

Celery Task Guidelines

Heavy tasks MUST be async via Celery:

· Bulk SMS/email notifications
· Bulk result upload processing
· Report generation
· Long-running imports/exports

```python
# tasks/async_tasks.py
@app.task
def process_bulk_result_upload(file_id, uploaded_by_id):
    # Heavy processing here
    pass
```

Testing Strategy

1. Unit Tests: Test selectors, services in isolation
2. Integration Tests: Test app boundaries (interfaces)
3. No Cross-App Test Dependencies: Each app's tests run independently

Deployment Considerations

· PostgreSQL required (SQLite not supported in production)
· Redis required for Celery
· Environment-based configuration (no hardcoded settings)

```