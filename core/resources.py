# core/resources.py
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from django.contrib.auth.hashers import make_password
from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark, Timetable
)


# ── User ───────────────────────────────────────────────────────────────────

class UserResource(resources.ModelResource):
    """
    Import rules:
      - Plain-text passwords are hashed automatically.
      - Blank password → unusable password (admin resets later).
      - system_admin role can only be imported by a superuser;
        otherwise the role is silently downgraded to school_admin.
      - is_superuser and is_staff flags are set correctly after each row.

    Export rules:
      - password and is_superuser are always excluded.
    """

    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )

    class Meta:
        model            = User
        import_id_fields = ('username',)   # match on username; never on id
        fields           = (
            'id', 'username', 'password', 'email',
            'first_name', 'last_name', 'role', 'school',
            'is_active', 'is_staff',
        )
        export_order     = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'school', 'is_active',
        )
        # Never expose these on export
        exclude          = ('password', 'is_superuser')
        skip_unchanged   = True
        report_skipped   = True

    # ── Before row ────────────────────────────────────────────────────────

    def before_import_row(self, row, **kwargs):
        """
        1. Block non-superusers from importing system_admin accounts.
        2. Hash plain-text passwords; set unusable password if blank.
        """
        # ── Role protection ───────────────────────────────────────────────
        request = kwargs.get('user')   # django-import-export passes request user here
        if row.get('role') == 'system_admin':
            is_superuser = request and getattr(request, 'is_superuser', False)
            if not is_superuser:
                # Silently downgrade — never let a school_admin import a superuser
                row['role'] = 'school_admin'

        # ── Password hashing ──────────────────────────────────────────────
        password = (row.get('password') or '').strip()
        if not password:
            # No password supplied → unusable until reset
            row['password'] = make_password(None)
        elif not password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
            # Plain text → hash it
            row['password'] = make_password(password)
        # Already hashed → leave as-is

    # ── After row ─────────────────────────────────────────────────────────

    def after_import_row(self, row, row_result, **kwargs):
        """
        Set is_superuser and is_staff correctly based on role.
        This runs after the row is saved so we can update the live object.
        """
        if row_result.errors:
            return

        try:
            user = User.objects.get(username=row.get('username'))
        except User.DoesNotExist:
            return

        if user.role == 'system_admin':
            # Full superuser access
            user.is_superuser = True
            user.is_staff     = True
            user.save(update_fields=['is_superuser', 'is_staff'])

        elif user.role in ('student', 'parent'):
            # No admin access at all
            if user.is_staff or user.is_superuser:
                user.is_staff     = False
                user.is_superuser = False
                user.save(update_fields=['is_staff', 'is_superuser'])

        else:
            # All other roles (teacher, dos, bursar, etc.) get staff access
            if not user.is_staff or user.is_superuser:
                user.is_staff     = True
                user.is_superuser = False
                user.save(update_fields=['is_staff', 'is_superuser'])

    # ── Export safety ─────────────────────────────────────────────────────

    def dehydrate_password(self, user):
        """Always return empty string on export — never expose password hash."""
        return ''


# ── School ─────────────────────────────────────────────────────────────────

class SchoolResource(resources.ModelResource):
    class Meta:
        model            = School
        import_id_fields = ('code',)
        fields           = ('id', 'name', 'code', 'address', 'phone', 'email')
        export_order     = ('id', 'name', 'code', 'address', 'phone', 'email')
        skip_unchanged   = True
        report_skipped   = True


# ── EmployeeProfile ────────────────────────────────────────────────────────

class EmployeeProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(User, field='username'),
    )
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )

    class Meta:
        model            = EmployeeProfile
        import_id_fields = ('user',)
        fields           = ('user', 'staff_id', 'hire_date', 'school')
        export_order     = ('user', 'staff_id', 'hire_date', 'school')
        skip_unchanged   = True
        report_skipped   = True


# ── ParentProfile ──────────────────────────────────────────────────────────

class ParentProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(User, field='username'),
    )
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )

    class Meta:
        model            = ParentProfile
        import_id_fields = ('user',)
        fields           = ('user', 'phone_number', 'school')
        export_order     = ('user', 'phone_number', 'school')
        skip_unchanged   = True
        report_skipped   = True


# ── Stream ─────────────────────────────────────────────────────────────────

class StreamResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )

    class Meta:
        model            = Stream
        import_id_fields = ('name', 'school')
        fields           = ('id', 'name', 'school')
        export_order     = ('id', 'name', 'school')
        skip_unchanged   = True
        report_skipped   = True


# ── ClassLevel ─────────────────────────────────────────────────────────────

class ClassLevelResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )
    class_teacher = fields.Field(
        column_name='class_teacher',
        attribute='class_teacher',
        widget=ForeignKeyWidget(EmployeeProfile, field='staff_id'),
    )

    class Meta:
        model            = ClassLevel
        import_id_fields = ('name', 'school')
        fields           = ('id', 'name', 'school', 'class_teacher')
        export_order     = ('id', 'name', 'school', 'class_teacher')
        skip_unchanged   = True
        report_skipped   = True


# ── StudentProfile ─────────────────────────────────────────────────────────

class StudentProfileResource(resources.ModelResource):
    user = fields.Field(
        column_name='username',
        attribute='user',
        widget=ForeignKeyWidget(User, field='username'),
    )
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )
    class_level = fields.Field(
        column_name='class_level',
        attribute='class_level',
        widget=ForeignKeyWidget(ClassLevel, field='name'),
    )
    stream = fields.Field(
        column_name='stream',
        attribute='stream',
        widget=ForeignKeyWidget(Stream, field='name'),
    )

    class Meta:
        model            = StudentProfile
        import_id_fields = ('admission_number',)
        fields           = (
            'user', 'admission_number', 'gender',
            'class_level', 'stream', 'school',
        )
        export_order     = (
            'user', 'admission_number', 'gender',
            'class_level', 'stream', 'school',
        )
        skip_unchanged   = True
        report_skipped   = True


# ── Subject ────────────────────────────────────────────────────────────────

class SubjectResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )

    class Meta:
        model            = Subject
        import_id_fields = ('code', 'school')
        fields           = ('id', 'name', 'code', 'school')
        export_order     = ('id', 'name', 'code', 'school')
        skip_unchanged   = True
        report_skipped   = True


# ── Mark ───────────────────────────────────────────────────────────────────

class MarkResource(resources.ModelResource):
    student = fields.Field(
        column_name='admission_number',
        attribute='student',
        widget=ForeignKeyWidget(StudentProfile, field='admission_number'),
    )
    subject = fields.Field(
        column_name='subject_code',
        attribute='subject',
        widget=ForeignKeyWidget(Subject, field='code'),
    )
    teacher = fields.Field(
        column_name='teacher_staff_id',
        attribute='teacher',
        widget=ForeignKeyWidget(EmployeeProfile, field='staff_id'),
    )
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )

    class Meta:
        model            = Mark
        import_id_fields = ('student', 'subject', 'term', 'exam', 'school')
        fields           = (
            'student', 'subject', 'teacher',
            'term', 'exam', 'mid_term', 'end_term', 'school',
        )
        export_order     = (
            'student', 'subject', 'teacher',
            'term', 'exam', 'mid_term', 'end_term', 'school',
        )
        skip_unchanged   = True
        report_skipped   = True


# ── Timetable ──────────────────────────────────────────────────────────────

class TimetableResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='name'),
    )
    class_level = fields.Field(
        column_name='class_level',
        attribute='class_level',
        widget=ForeignKeyWidget(ClassLevel, field='name'),
    )
    stream = fields.Field(
        column_name='stream',
        attribute='stream',
        widget=ForeignKeyWidget(Stream, field='name'),
    )
    subject = fields.Field(
        column_name='subject',
        attribute='subject',
        widget=ForeignKeyWidget(Subject, field='code'),
    )
    teacher = fields.Field(
        column_name='teacher',
        attribute='teacher',
        widget=ForeignKeyWidget(EmployeeProfile, field='staff_id'),
    )

    class Meta:
        model            = Timetable
        import_id_fields = ('class_level', 'stream', 'subject', 'day', 'start_time', 'school')
        fields           = (
            'school', 'class_level', 'stream', 'subject',
            'teacher', 'day', 'start_time', 'end_time', 'room',
        )
        export_order     = (
            'school', 'class_level', 'stream', 'subject',
            'teacher', 'day', 'start_time', 'end_time', 'room',
        )
        skip_unchanged   = True
        report_skipped   = True