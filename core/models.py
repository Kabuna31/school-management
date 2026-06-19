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
    ('school_admin',   'School System Administrator'),
    ('headteacher',    'Headteacher'),
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
    stream           = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True)
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


# 6 exam slots per year
EXAM_CHOICES = [
    ('T1_Mid', 'Term 1 — Mid Term'),
    ('T1_End', 'Term 1 — End of Term'),
    ('T2_Mid', 'Term 2 — Mid Term'),
    ('T2_End', 'Term 2 — End of Term'),
    ('T3_Mid', 'Term 3 — Mid Term'),
    ('T3_End', 'Term 3 — End of Term'),
]

# Map exam → parent term (for grouping in report cards)
EXAM_TERM_MAP = {
    'T1_Mid': 'Term 1', 'T1_End': 'Term 1',
    'T2_Mid': 'Term 2', 'T2_End': 'Term 2',
    'T3_Mid': 'Term 3', 'T3_End': 'Term 3',
}

class Mark(models.Model):
    school   = models.ForeignKey(School,         on_delete=models.CASCADE)
    student  = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject  = models.ForeignKey(Subject,        on_delete=models.CASCADE)
    teacher  = models.ForeignKey(
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    exam     = models.CharField(max_length=10, choices=EXAM_CHOICES)
    score    = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('school', 'student', 'subject', 'exam')

    def __str__(self):
        return f"{self.student} — {self.subject} {self.get_exam_display()}: {self.score}"

    @property
    def grade(self):
        s = float(self.score)
        if s >= 80: return 'A'
        if s >= 65: return 'B'
        if s >= 50: return 'C'
        return 'F'

    @property
    def term(self):
        return EXAM_TERM_MAP.get(self.exam, '')


# ---------------------------------------------------------------------------
# 6. Timetable
# ---------------------------------------------------------------------------
DAY_CHOICES = [
    ('Mon', 'Monday'), ('Tue', 'Tuesday'), ('Wed', 'Wednesday'),
    ('Thu', 'Thursday'), ('Fri', 'Friday'),
]

class Timetable(models.Model):
    school      = models.ForeignKey(School,         on_delete=models.CASCADE)
    class_level = models.ForeignKey(ClassLevel,     on_delete=models.CASCADE)
    stream      = models.ForeignKey(Stream,         on_delete=models.SET_NULL, null=True, blank=True)
    subject     = models.ForeignKey(Subject,        on_delete=models.CASCADE)
    teacher     = models.ForeignKey(EmployeeProfile,on_delete=models.SET_NULL, null=True, blank=True)
    day         = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    room        = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.class_level} {self.get_day_display()} {self.start_time}–{self.end_time} {self.subject}"
