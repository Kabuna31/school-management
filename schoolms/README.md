# SchoolMS

A Django-based school management system.

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy config files into your Django project:
#    - config/settings.py  → config/settings.py
#    - config/urls.py      → config/urls.py
#    - core/               → core/
#    - templates/          → templates/
#    - static/             → static/

# 4. Run migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Run server
python manage.py runserver
```

## Role → Dashboard mapping

| Role          | Dashboard URL              |
|---------------|----------------------------|
| system_admin  | /dashboard/superuser/      |
| headteacher   | /dashboard/headteacher/    |
| dos           | /dashboard/dos/            |
| bursar        | /dashboard/bursar/         |
| teacher       | /dashboard/teacher/        |
| class_teacher | /dashboard/teacher/        |
| student       | /dashboard/student/        |
| parent        | /dashboard/parent/         |

## First steps after setup

1. Go to /admin/ and log in
2. Add a School
3. Assign your superuser role = system_admin and a school
4. Add Streams (e.g. A, B, West)
5. Add Class Levels (e.g. S1, S2, S3)
6. Add Subjects
7. Add Users (teachers, students, parents)
8. Add Employee/Student/Parent profiles
9. Enter marks via /marks/entry/
