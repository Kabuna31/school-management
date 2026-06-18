"""
core/resources.py

Import/Export resource definitions for all major models.
Uses django-import-export (already in requirements.txt).
"""
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export import resources, fields

from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark
)


# ── School ─────────────────────────────────────────────────────────────────

class SchoolResource(resources.ModelResource):
    class Meta:
        model  = School
        fields = ('id', 'name', 'code', 'created_at')
        export_order = ('id', 'name', 'code', 'created_at')
        import_id_fields = ('code',)  # use code as natural key


# ── User ───────────────────────────────────────────────────────────────────


class UserResource(resources.ModelResource):

    school = fields.Field(
        column_name="school",
        attribute="school",
        widget=ForeignKeyWidget(
            School,
            field="code"
        )
    )

    class Meta:
        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "school",
            "is_active",
        )

        export_order = fields
        import_id_fields = ("username",)

    def before_import_row(self, row, **kwargs):

        school_code = row.get("school")

        if school_code:
            School.objects.get_or_create(
                code=school_code,
                defaults={
                    "name": school_code
                }
            )

    def after_save_instance(
        self,
        instance,
        row,
        **kwargs
    ):
        """
        Password = username
        """

        if row.get("username"):

            instance.set_password(
                row["username"]
            )

            instance.save()
# ── EmployeeProfile ────────────────────────────────────────────────────────

class EmployeeProfileResource(resources.ModelResource):
    username  = fields.Field(column_name='username',  attribute='user__username')
    full_name = fields.Field(column_name='full_name', attribute='user__get_full_name')
    school    = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='code')
    )
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='username')
    )

    class Meta:
        model  = EmployeeProfile
        fields = ('user', 'username', 'full_name', 'school', 'staff_id', 'hire_date')
        export_order = ('user', 'username', 'full_name', 'school', 'staff_id', 'hire_date')
        import_id_fields = ('user',)


# ── Stream ─────────────────────────────────────────────────────────────────

class StreamResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='code')
    )

    class Meta:
        model  = Stream
        fields = ('id', 'name', 'school')
        export_order = ('id', 'school', 'name')
        import_id_fields = ('id',)


# ── ClassLevel ─────────────────────────────────────────────────────────────

class ClassLevelResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='code')
    )
    class_teacher = fields.Field(
        column_name='class_teacher',
        attribute='class_teacher',
        widget=ForeignKeyWidget(EmployeeProfile, field='staff_id')
    )

    class Meta:
        model  = ClassLevel
        fields = ('id', 'name', 'school', 'class_teacher')
        export_order = ('id', 'school', 'name', 'class_teacher')
        import_id_fields = ('id',)


# ── StudentProfile ─────────────────────────────────────────────────────────

class StudentProfileResource(resources.ModelResource):
    username   = fields.Field(column_name='username',   attribute='user__username')
    first_name = fields.Field(column_name='first_name', attribute='user__first_name')
    last_name  = fields.Field(column_name='last_name',  attribute='user__last_name')
    email      = fields.Field(column_name='email',      attribute='user__email')

    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='code')
    )
    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, field='username')
    )
    class_level = fields.Field(
        column_name='class_level',
        attribute='class_level',
        widget=ForeignKeyWidget(ClassLevel, field='name')
    )
    stream = fields.Field(
        column_name='stream',
        attribute='stream',
        widget=ForeignKeyWidget(Stream, field='name')
    )

    class Meta:
        model  = StudentProfile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'email',
            'school', 'admission_number', 'gender', 'class_level', 'stream'
        )
        export_order = (
            'user', 'username', 'first_name', 'last_name', 'email',
            'school', 'admission_number', 'gender', 'class_level', 'stream'
        )
        import_id_fields = ('user',)


# ── Subject ────────────────────────────────────────────────────────────────

class SubjectResource(resources.ModelResource):
    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='code')
    )

    class Meta:
        model  = Subject
        fields = ('id', 'name', 'code', 'school')
        export_order = ('id', 'school', 'name', 'code')
        import_id_fields = ('id',)


# ── Mark ───────────────────────────────────────────────────────────────────

class MarkResource(resources.ModelResource):
    student_name     = fields.Field(column_name='student_name',     attribute='student__user__get_full_name')
    admission_number = fields.Field(column_name='admission_number', attribute='student__admission_number')
    subject_name     = fields.Field(column_name='subject_name',     attribute='subject__name')
    teacher_name     = fields.Field(column_name='teacher_name',     attribute='teacher__user__get_full_name')
    class_level      = fields.Field(column_name='class_level',      attribute='student__class_level__name')
    stream           = fields.Field(column_name='stream',           attribute='student__stream__name')

    school = fields.Field(
        column_name='school',
        attribute='school',
        widget=ForeignKeyWidget(School, field='code')
    )
    student = fields.Field(
        column_name='student',
        attribute='student',
        widget=ForeignKeyWidget(StudentProfile, field='admission_number')
    )
    subject = fields.Field(
        column_name='subject',
        attribute='subject',
        widget=ForeignKeyWidget(Subject, field='code')
    )
    teacher = fields.Field(
        column_name='teacher',
        attribute='teacher',
        widget=ForeignKeyWidget(EmployeeProfile, field='staff_id')
    )

    class Meta:
        model  = Mark
        fields = (
            'id', 'school', 'student', 'admission_number', 'student_name',
            'class_level', 'stream', 'subject', 'subject_name',
            'term', 'score', 'teacher', 'teacher_name'
        )
        export_order = (
            'id', 'school', 'student', 'admission_number', 'student_name',
            'class_level', 'stream', 'subject', 'subject_name',
            'term', 'score', 'teacher', 'teacher_name'
        )
        import_id_fields = ('id',)
