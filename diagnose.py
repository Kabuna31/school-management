# diagnose.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import School, ClassLevel, Stream, Subject, StudentProfile, Mark, EmployeeProfile
from django.db import connection

User = get_user_model()

print("=" * 60)
print("SCHOOL MANAGEMENT SYSTEM - DIAGNOSIS")
print("=" * 60)

# 1. Check Database Connection
print("\n1. DATABASE CONNECTION:")
print("-" * 40)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✅ Database connection: OK")
except Exception as e:
    print(f"❌ Database connection: FAILED - {e}")

# 2. Check Schools
print("\n2. SCHOOLS:")
print("-" * 40)
schools = School.objects.all()
print(f"Total schools: {schools.count()}")
for school in schools:
    print(f"  - ID: {school.id}, Name: {school.name}, Code: {school.code}")

if schools.count() == 0:
    print("⚠️ No schools found! This is the root cause of many issues.")
    print("   Please create a school using: python manage.py shell")
    print("   >>> from core.models import School")
    print("   >>> School.objects.create(name='Default School', code='DS001')")

# 3. Check Users
print("\n3. USERS:")
print("-" * 40)
users = User.objects.all()
print(f"Total users: {users.count()}")
print(f"  - Active users: {users.filter(is_active=True).count()}")
print(f"  - Superusers: {users.filter(is_superuser=True).count()}")
print(f"  - Staff: {users.filter(is_staff=True).count()}")

# Check users without school
users_without_school = users.filter(school__isnull=True)
if users_without_school.exists():
    print(f"⚠️ {users_without_school.count()} users have NO school assigned:")
    for user in users_without_school[:5]:
        print(f"    - {user.username} (Role: {user.role})")
else:
    print("✅ All users have a school assigned")

# Check users with school
print("\nUsers with school:")
for user in users.filter(school__isnull=False)[:10]:
    print(f"  - {user.username} → {user.school.name}")

# 4. Check Class Levels
print("\n4. CLASS LEVELS:")
print("-" * 40)
class_levels = ClassLevel.objects.all()
print(f"Total class levels: {class_levels.count()}")

# Check class levels without school
class_levels_without_school = class_levels.filter(school__isnull=True)
if class_levels_without_school.exists():
    print(f"⚠️ {class_levels_without_school.count()} class levels have NO school:")
    for cls in class_levels_without_school:
        print(f"    - {cls.name} (ID: {cls.id})")
else:
    print("✅ All class levels have a school assigned")

# 5. Check Streams
print("\n5. STREAMS:")
print("-" * 40)
streams = Stream.objects.all()
print(f"Total streams: {streams.count()}")

streams_without_school = streams.filter(school__isnull=True)
if streams_without_school.exists():
    print(f"⚠️ {streams_without_school.count()} streams have NO school:")
    for stream in streams_without_school:
        print(f"    - {stream.name} (ID: {stream.id})")
else:
    print("✅ All streams have a school assigned")

# 6. Check Subjects
print("\n6. SUBJECTS:")
print("-" * 40)
subjects = Subject.objects.all()
print(f"Total subjects: {subjects.count()}")

subjects_without_school = subjects.filter(school__isnull=True)
if subjects_without_school.exists():
    print(f"⚠️ {subjects_without_school.count()} subjects have NO school:")
    for subject in subjects_without_school:
        print(f"    - {subject.name} (ID: {subject.id})")
else:
    print("✅ All subjects have a school assigned")

# 7. Check Student Profiles
print("\n7. STUDENT PROFILES:")
print("-" * 40)
students = StudentProfile.objects.all()
print(f"Total students: {students.count()}")

students_without_school = students.filter(school__isnull=True)
if students_without_school.exists():
    print(f"⚠️ {students_without_school.count()} students have NO school:")
    for student in students_without_school[:5]:
        print(f"    - {student.user.username} (Admission: {student.admission_number})")
else:
    print("✅ All students have a school assigned")

# 8. Check Employee Profiles
print("\n8. EMPLOYEE PROFILES:")
print("-" * 40)
employees = EmployeeProfile.objects.all()
print(f"Total employees: {employees.count()}")

employees_without_school = employees.filter(school__isnull=True)
if employees_without_school.exists():
    print(f"⚠️ {employees_without_school.count()} employees have NO school:")
    for emp in employees_without_school[:5]:
        print(f"    - {emp.user.username} (Staff ID: {emp.staff_id})")
else:
    print("✅ All employees have a school assigned")

# 9. Check Marks
print("\n9. MARKS:")
print("-" * 40)
marks = Mark.objects.all()
print(f"Total marks: {marks.count()}")

marks_without_school = marks.filter(school__isnull=True)
if marks_without_school.exists():
    print(f"⚠️ {marks_without_school.count()} marks have NO school:")
    for mark in marks_without_school[:5]:
        print(f"    - {mark.student.user.username} → {mark.subject.name}")
else:
    print("✅ All marks have a school assigned")

# 10. Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

issues_found = 0

if schools.count() == 0:
    print("❌ CRITICAL: No schools exist! Create one immediately.")
    issues_found += 1

if users_without_school.exists():
    print(f"⚠️ {users_without_school.count()} users need school assigned.")
    issues_found += 1

if class_levels_without_school.exists():
    print(f"⚠️ {class_levels_without_school.count()} class levels need school assigned.")
    issues_found += 1

if streams_without_school.exists():
    print(f"⚠️ {streams_without_school.count()} streams need school assigned.")
    issues_found += 1

if subjects_without_school.exists():
    print(f"⚠️ {subjects_without_school.count()} subjects need school assigned.")
    issues_found += 1

if students_without_school.exists():
    print(f"⚠️ {students_without_school.count()} students need school assigned.")
    issues_found += 1

if issues_found == 0:
    print("✅ No issues found! Your system is healthy.")
else:
    print(f"\nTotal issues found: {issues_found}")
    print("\nTo fix these issues, run:")
    print("  python manage.py shell")
    print("  >>> from core.models import School, User")
    print("  >>> school = School.objects.first()")
    print("  >>> for user in User.objects.all():")
    print("  ...     if not user.school:")
    print("  ...         user.school = school")
    print("  ...         user.save()")

print("=" * 60)