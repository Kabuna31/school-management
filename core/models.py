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

SCOPED_ROLES = [
    'school_admin', 'headteacher', 'dos', 'bursar',
    'nurse', 'librarian', 'lab_technician', 'class_teacher',
    'teacher', 'parent', 'student',
]

MARK_ENTRY_ROLES = [
    'system_admin', 'school_admin', 'headteacher',
    'dos', 'teacher', 'class_teacher',
]

MARK_MANAGE_ROLES = ['school_admin', 'headteacher']

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
        if t >= 70: return 'B'
        if t >= 60: return 'C'
        if t >= 50: return 'D'
        return 'E'

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
# 6. Report Cards
# ---------------------------------------------------------------------------

class ReportCard(models.Model):
    """
    One report card per student per term.
    Covers both Mid Term and End of Term marks combined on one card.
    """
    school          = models.ForeignKey(School, on_delete=models.CASCADE)
    student         = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='report_cards')
    term            = models.CharField(max_length=10, choices=TERM_CHOICES)
    class_level     = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True)
    stream          = models.ForeignKey(Stream, on_delete=models.SET_NULL, null=True, blank=True)
    class_position  = models.PositiveIntegerField(null=True, blank=True)
    total_students  = models.PositiveIntegerField(null=True, blank=True)
    aggregate_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    teacher_comment    = models.TextField(blank=True)
    headteacher_remark = models.TextField(blank=True)
    generated_by    = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generated_report_cards',
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school', 'student', 'term')
        ordering        = ['term', 'student']

    def __str__(self):
        return f"{self.student} — {self.term} Report Card"

    @property
    def total_grade_points(self):
        return sum(e.grade_points for e in self.entries.all())

    @property
    def average_score(self):
        entries = list(self.entries.all())
        if not entries:
            return 0
        return round(sum(e.total for e in entries) / len(entries), 1)


class ReportCardEntry(models.Model):
    """One subject row on a report card."""
    report_card = models.ForeignKey(ReportCard, on_delete=models.CASCADE, related_name='entries')
    subject     = models.ForeignKey(Subject, on_delete=models.CASCADE)
    mid_term    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    end_term    = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('report_card', 'subject')
        ordering        = ['subject__name']

    def __str__(self):
        return f"{self.report_card} — {self.subject}"

    @property
    def total(self):
        return float(self.mid_term or 0) + float(self.end_term or 0)

    @property
    def grade(self):
        t = self.total
        if t >= 80: return 'A'
        if t >= 70: return 'B'
        if t >= 60: return 'C'
        if t >= 50: return 'D'
        return 'E'

    @property
    def grade_points(self):
        t = self.total
        if t >= 80: return 5
        if t >= 70: return 4
        if t >= 60: return 3
        if t >= 50: return 2
        return 1

# ---------------------------------------------------------------------------
# 7. Timetable
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
