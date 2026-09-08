from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


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


# ---------------------------------------------------------------------------
# 8. Elections / Voting
# ---------------------------------------------------------------------------

class Election(models.Model):
    """A voting event, e.g. 'Student Council Elections 2026'."""
    school       = models.ForeignKey(School, on_delete=models.CASCADE)
    title        = models.CharField(max_length=150)
    description  = models.TextField(blank=True)
    start_time   = models.DateTimeField()
    end_time     = models.DateTimeField()
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_elections',
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.title} ({self.school})"

    @property
    def is_open(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Election start_time must be before end_time.")


class Position(models.Model):
    """A role being contested, e.g. 'Head Prefect', 'Sports Prefect'."""
    election     = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='positions')
    title        = models.CharField(max_length=100)
    description  = models.TextField(blank=True)
    max_votes_per_voter = models.PositiveIntegerField(
        default=1,
        help_text="How many candidates a student may select for this position (usually 1).",
    )
    order        = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']
        unique_together = ('election', 'title')

    def __str__(self):
        return f"{self.title} — {self.election.title}"


class Candidate(models.Model):
    school       = models.ForeignKey(School, on_delete=models.CASCADE)
    position     = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates')
    student      = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='candidacies')
    manifesto    = models.TextField(blank=True)
    photo        = models.ImageField(upload_to='election/candidates/', blank=True, null=True)
    is_approved  = models.BooleanField(
        default=False,
        help_text="Candidate must be approved (e.g. by DOS/headteacher) before appearing on the ballot.",
    )

    class Meta:
        unique_together = ('position', 'student')
        ordering = ['student__user__first_name']

    def __str__(self):
        return f"{self.student} — {self.position.title}"

    def clean(self):
        super().clean()
        if self.student_id and self.school_id and self.student.school_id != self.school_id:
            raise ValidationError("Candidate's student must belong to the same school.")
        if self.position_id and self.position.election.school_id != self.school_id:
            raise ValidationError("Candidate's school must match the election's school.")

    @property
    def vote_count(self):
        return self.votes.count()


class Vote(models.Model):
    """
    One vote cast by a student for one candidate in one position.

    Uniqueness on (position, candidate, voter) prevents voting for the same
    candidate twice. The actual "max N votes per position" rule is enforced
    in clean() since max_votes_per_voter can exceed 1, which a simple unique
    constraint can't express.
    """
    school    = models.ForeignKey(School, on_delete=models.CASCADE)
    position  = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='votes')
    voter     = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='votes_cast')
    cast_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('position', 'candidate', 'voter')
        ordering = ['-cast_at']

    def __str__(self):
        return f"{self.voter} → {self.candidate} ({self.position.title})"

    def clean(self):
        super().clean()

        if self.candidate_id and self.position_id and self.candidate.position_id != self.position_id:
            raise ValidationError("Candidate does not belong to this position.")

        if self.candidate_id and not self.candidate.is_approved:
            raise ValidationError("Cannot vote for an unapproved candidate.")

        if self.voter_id and self.school_id and self.voter.school_id != self.school_id:
            raise ValidationError("Voter must belong to the same school as the election.")

        election = self.position.election if self.position_id else None
        if election and not election.is_open:
            raise ValidationError("Voting is closed for this election.")

        if self.position_id and self.voter_id:
            existing = Vote.objects.filter(
                position=self.position, voter=self.voter
            ).exclude(pk=self.pk).count()
            if existing >= self.position.max_votes_per_voter:
                raise ValidationError(
                    f"You may only vote for {self.position.max_votes_per_voter} "
                    f"candidate(s) for {self.position.title}."
                )


class SchoolSettings(models.Model):
    """School-specific settings for report cards and branding"""
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name='settings')
    
    # School Information
    school_name = models.CharField(max_length=200, blank=True)
    school_address = models.TextField(blank=True)
    school_phone = models.CharField(max_length=100, blank=True)
    school_email = models.EmailField(blank=True)
    school_website = models.URLField(blank=True)
    school_logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    school_motto = models.CharField(max_length=200, blank=True)
    
    # Report Card Settings
    report_card_title = models.CharField(max_length=100, default='ACADEMIC REPORT CARD')
    header_text = models.TextField(blank=True, help_text='Custom header text to appear on report cards')
    footer_text = models.TextField(blank=True, help_text='Custom footer text to appear on report cards')
    show_grade_scale = models.BooleanField(default=True)
    show_teacher_signature = models.BooleanField(default=True)
    show_head_teacher_signature = models.BooleanField(default=True)
    
    # Grade Scale Customization
    grade_a_min = models.IntegerField(default=80, validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_b_min = models.IntegerField(default=70, validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_c_min = models.IntegerField(default=60, validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_d_min = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_e_min = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    grade_a_label = models.CharField(max_length=50, default='Exceptional')
    grade_b_label = models.CharField(max_length=50, default='Outstanding')
    grade_c_label = models.CharField(max_length=50, default='Satisfactory')
    grade_d_label = models.CharField(max_length=50, default='Basic')
    grade_e_label = models.CharField(max_length=50, default='Elementary')
    
    # Subject Performance Labels
    subject_columns = models.JSONField(default=list, blank=True)
    
    # Colors & Styling
    primary_color = models.CharField(max_length=7, default='#1a237e')
    secondary_color = models.CharField(max_length=7, default='#0d47a1')
    accent_color = models.CharField(max_length=7, default='#e8eaf6')
    
    # Terms
    term_dates = models.JSONField(default=dict, blank=True)
    
    # Custom Fields
    custom_fields = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Settings for {self.school.name}"
    
    class Meta:
        verbose_name = "School Settings"
        verbose_name_plural = "School Settings"