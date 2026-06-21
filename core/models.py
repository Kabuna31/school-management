from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# 1. School
# ---------------------------------------------------------------------------
class School(models.Model):
    name    = models.CharField(max_length=255)
    code    = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone   = models.CharField(max_length=30,  blank=True, null=True)
    email   = models.EmailField(blank=True, null=True)
    logo    = models.ImageField(upload_to="school_logos/", blank=True, null=True)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 2. User
# ---------------------------------------------------------------------------
ROLE_CHOICES = (
    ('system_admin',   'System Admin'),
    ('school_admin',   'School System Administrator'),
    ('headteacher',    'Headteacher'),
    ('dos',            'Director of Studies'),
    ('bursar',         'School Bursar'),
    ('nurse',          'School Nurse'),
    ('librarian',      'School Librarian'),
    ('lab_technician', 'Lab Technician'),
    ('class_teacher',  'Class Teacher'),
    ('teacher',        'Teacher'),
    ('parent',         'Parent'),
    ('student',        'Student'),
)

# Roles that are scoped to their own school (used by admin + views).
# Every role that gets a school assigned must be listed here so that
# admin querysets, dropdowns, and save logic restrict them correctly.
# system_admin is intentionally excluded — they see all schools.
SCOPED_ROLES = [
    'school_admin', 'headteacher', 'dos', 'bursar',
    'nurse', 'librarian', 'lab_technician', 'class_teacher',
    'teacher', 'parent', 'student',
]

# Roles that can enter / edit marks
MARK_ENTRY_ROLES = [
    'system_admin', 'school_admin', 'headteacher',
    'dos', 'teacher', 'class_teacher',
]

# Roles that can manage (view/edit/delete) all school marks
MARK_MANAGE_ROLES = ['school_admin', 'headteacher']

# Roles that have a dedicated dashboard (others fall back to /admin/)
DASHBOARD_ROLES = [
    'system_admin', 'school_admin', 'headteacher', 'dos',
    'bursar', 'teacher', 'class_teacher', 'student', 'parent',
    'nurse', 'librarian', 'lab_technician',
]


class User(AbstractUser):
    """
    Custom User model with school scoping.

    Rules enforced in clean():
    - system_admin: MUST have school = None (sees all schools)
    - All other roles: MUST have a school assigned
    """
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="School assignment. Leave blank ONLY for System Admin.",
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='teacher',
    )

    def __str__(self):
        school = self.school.name if self.school_id else "No School"
        return f"{self.get_full_name() or self.username} ({self.get_role_display()}) — {school}"

    @property
    def is_system_admin(self):
        return self.role == 'system_admin' or self.is_superuser

    @property
    def is_scoped_role(self):
        """True for roles that should only see their own school's data."""
        return self.role in SCOPED_ROLES

    def clean(self):
        """
        Called by Django forms and admin (not by save()).
        Validates school/role consistency so errors surface cleanly in the UI.
        """
        super().clean()

        if self.role == 'system_admin' and self.school_id:
            raise ValidationError({
                'school': (
                    "System Admin users cannot be assigned to a specific school. "
                    "They see all schools."
                )
            })

        if self.role != 'system_admin' and not self.school_id:
            raise ValidationError({
                'school': (
                    f"School is required for {self.get_role_display()} users. "
                    "Only System Admin can have no school."
                )
            })

    def save(self, *args, **kwargs):
        """
        Auto-correct system_admin fields before saving.
        Validation is intentionally left to clean() / forms so that
        programmatic saves (management commands, signals, tests) do not
        raise ValidationError unexpectedly.
        """
        if self.role == 'system_admin':
            self.school    = None
            self.school_id = None
            self.is_superuser = True
            self.is_staff     = True
        super().save(*args, **kwargs)


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

    def clean(self):
        """Ensure the employee's school matches the linked user's school."""
        super().clean()
        if self.user_id and self.school_id:
            if self.user.school_id != self.school_id:
                raise ValidationError(
                    "Employee profile school must match the linked user's school."
                )


class ParentProfile(models.Model):
    school       = models.ForeignKey(School, on_delete=models.CASCADE)
    user         = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def clean(self):
        """Ensure the parent's school matches the linked user's school."""
        super().clean()
        if self.user_id and self.school_id:
            if self.user.school_id != self.school_id:
                raise ValidationError(
                    "Parent profile school must match the linked user's school."
                )


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
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='class_teacher_of',
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
    passport_photo   = models.ImageField(
        upload_to='students/passports/',
        blank=True,
        null=True,
        default='students/passports/default.png',
    )

    class Meta:
        unique_together = ('school', 'admission_number')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.admission_number})"

    def clean(self):
        """Ensure the student's school matches the linked user's school."""
        super().clean()
        if self.user_id and self.school_id:
            if self.user.school_id != self.school_id:
                raise ValidationError(
                    "Student profile school must match the linked user's school."
                )


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


TERM_CHOICES = [
    ('Term 1', 'Term 1'),
    ('Term 2', 'Term 2'),
    ('Term 3', 'Term 3'),
]

EXAM_CHOICES = [
    ('Mid Term',    'Mid Term'),
    ('End of Term', 'End of Term'),
]

EXAM_LABEL_MAP = {
    ('Term 1', 'Mid Term'):    'Term 1 — Mid Term',
    ('Term 1', 'End of Term'): 'Term 1 — End of Term',
    ('Term 2', 'Mid Term'):    'Term 2 — Mid Term',
    ('Term 2', 'End of Term'): 'Term 2 — End of Term',
    ('Term 3', 'Mid Term'):    'Term 3 — Mid Term',
    ('Term 3', 'End of Term'): 'Term 3 — End of Term',
}


class Mark(models.Model):
    school  = models.ForeignKey(School,         on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject,        on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True,
    )
    term     = models.CharField(max_length=10, choices=TERM_CHOICES)
    exam     = models.CharField(max_length=15, choices=EXAM_CHOICES)
    mid_term = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    end_term = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('school', 'student', 'subject', 'term', 'exam')

    def __str__(self):
        label = EXAM_LABEL_MAP.get((self.term, self.exam), f"{self.term} {self.exam}")
        return f"{self.student} — {self.subject} {label}"

    @property
    def total_score(self):
        return float(self.mid_term or 0) + float(self.end_term or 0)

    @property
    def grade(self):
        t = self.total_score
        if t >= 80: return 'A'
        if t >= 65: return 'B'
        if t >= 50: return 'C'
        return 'F'

    @property
    def grade_points(self):
        """Uganda-style grade points for report card aggregation."""
        t = self.total_score
        if t >= 80: return 5
        if t >= 70: return 4
        if t >= 60: return 3
        if t >= 50: return 2
        return 1


# ---------------------------------------------------------------------------
# 6. Timetable
# ---------------------------------------------------------------------------
DAY_CHOICES = [
    ('Mon', 'Monday'), ('Tue', 'Tuesday'), ('Wed', 'Wednesday'),
    ('Thu', 'Thursday'), ('Fri', 'Friday'),
]


class Timetable(models.Model):
    school      = models.ForeignKey(School,          on_delete=models.CASCADE)
    class_level = models.ForeignKey(ClassLevel,      on_delete=models.CASCADE)
    stream      = models.ForeignKey(Stream,          on_delete=models.SET_NULL, null=True, blank=True)
    subject     = models.ForeignKey(Subject,         on_delete=models.CASCADE)
    teacher     = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True)
    day         = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    room        = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering        = ['day', 'start_time']
        unique_together = ('school', 'class_level', 'stream', 'subject', 'day', 'start_time')

    def __str__(self):
        return (
            f"{self.class_level} {self.get_day_display()} "
            f"{self.start_time}–{self.end_time} {self.subject}"
        )
