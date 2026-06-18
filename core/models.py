from django.db import models
from django.contrib.auth.models import AbstractUser


# ---------------------------------------------------------------------------
# 1. School
# ---------------------------------------------------------------------------
class School(models.Model):
    name       = models.CharField(max_length=255)
    code       = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 2. User
# ---------------------------------------------------------------------------
ROLE_CHOICES = (
    ('system_admin',   'System Admin'),
    ('headteacher',    'School Administrator'),
    ('bursar',         'School Bursar'),
    ('nurse',          'School Nurse'),
    ('librarian',      'School Librarian'),
    ('lab_technician', 'Lab Technician'),
    ('dos',            'Director of Studies'),
    ('class_teacher',  'Class Teacher'),
    ('teacher',        'Teacher'),
    ('parent',         'Parent'),
    ('student',        'Student'),
)

class User(AbstractUser):
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, null=True, blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='teacher')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_system_admin(self):
        return self.role == 'system_admin' or self.is_superuser


# ---------------------------------------------------------------------------
# 3. Profiles
# ---------------------------------------------------------------------------
class EmployeeProfile(models.Model):
    school    = models.ForeignKey(School, on_delete=models.CASCADE)
    user      = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    staff_id  = models.CharField(max_length=50)
    hire_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('school', 'staff_id')

    def __str__(self):
        return f"{self.user.get_full_name()} [{self.staff_id}]"


class ParentProfile(models.Model):
    school       = models.ForeignKey(School, on_delete=models.CASCADE)
    user         = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


# ---------------------------------------------------------------------------
# 4. Academic structure
# ---------------------------------------------------------------------------
class Stream(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name   = models.CharField(max_length=50)

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    school        = models.ForeignKey(School, on_delete=models.CASCADE)
    name          = models.CharField(max_length=50)
    class_teacher = models.ForeignKey(
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    school           = models.ForeignKey(School, on_delete=models.CASCADE)
    user             = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    admission_number = models.CharField(max_length=20)
    gender           = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')])
    class_level      = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True)
    stream           = models.ForeignKey(Stream,     on_delete=models.SET_NULL, null=True, blank=True)
    parent           = models.ManyToManyField(ParentProfile, related_name='children', blank=True)

    class Meta:
        unique_together = ('school', 'admission_number')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.admission_number})"


# ---------------------------------------------------------------------------
# 5. Subjects & Marks
# ---------------------------------------------------------------------------
class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name   = models.CharField(max_length=100)
    code   = models.CharField(max_length=10)

    class Meta:
        unique_together = ('school', 'code')

    def __str__(self):
        return f"{self.name} ({self.code})"


class Mark(models.Model):
    TERM_CHOICES = [
        ('Term 1', 'Term 1'),
        ('Term 2', 'Term 2'),
        ('Term 3', 'Term 3'),
    ]

    school   = models.ForeignKey(School,         on_delete=models.CASCADE)
    student  = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject  = models.ForeignKey(Subject,        on_delete=models.CASCADE)
    teacher  = models.ForeignKey(
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    term     = models.CharField(max_length=20, choices=TERM_CHOICES)
    score    = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('school', 'student', 'subject', 'term')

    def __str__(self):
        return f"{self.student} — {self.subject} {self.term}: {self.score}"
