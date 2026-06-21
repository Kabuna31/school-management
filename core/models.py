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

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    ROLE_CHOICES = [
        ("system_admin", "System Administrator"),
        ("school_admin", "School Administrator"),
        ("headteacher", "Headteacher"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES
    )

    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    def clean(self):
        super().clean()

        # Only system admin can have no school
        if self.role != "system_admin" and self.school is None:
            raise ValidationError({
                "school": "School is required for this user role."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
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


# Term choices — stored directly on Mark so views can filter by DB field
TERM_CHOICES = [
    ('Term 1', 'Term 1'),
    ('Term 2', 'Term 2'),
    ('Term 3', 'Term 3'),
]

# Exam slot choices within a term
EXAM_CHOICES = [
    ('Mid Term', 'Mid Term'),
    ('End of Term', 'End of Term'),
]

# Combined label used in __str__ and displays
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
        EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Stored as DB fields so views can filter/annotate on them
    term    = models.CharField(max_length=10, choices=TERM_CHOICES)
    exam    = models.CharField(max_length=15, choices=EXAM_CHOICES)

    # Two score columns: mid-term and end-of-term within the same record
    mid_term = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    end_term = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        # One record per student/subject/term/exam slot
        unique_together = ('school', 'student', 'subject', 'term', 'exam')

    def __str__(self):
        label = EXAM_LABEL_MAP.get((self.term, self.exam), f"{self.term} {self.exam}")
        return f"{self.student} — {self.subject} {label}"

    # ------------------------------------------------------------------
    # Computed helpers (read-only; not stored)
    # ------------------------------------------------------------------
    @property
    def total_score(self):
        """Combined score used for grading."""
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
