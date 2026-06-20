from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Avg, ExpressionWrapper, F, FloatField

from import_export.admin import ImportExportModelAdmin
from .resources import UserResource, SchoolResource, EmployeeProfileResource, StudentProfileResource

from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark, Timetable,
)
from .resources import (
    SchoolResource, UserResource, EmployeeProfileResource,
    ParentProfileResource, StreamResource, ClassLevelResource,
    StudentProfileResource, SubjectResource, MarkResource,
    TimetableResource
)

# ============================================================
# Resources (Define how data is imported/exported)
# ============================================================

class SchoolResource(resources.ModelResource):
    class Meta:
        model = School
        fields = ('id', 'name', 'code', 'address', 'phone', 'email')
        export_order = fields


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'school', 'is_active')
        export_order = fields


class EmployeeProfileResource(resources.ModelResource):
    class Meta:
        model = EmployeeProfile
        fields = ('id', 'user', 'staff_id', 'hire_date', 'school')
        export_order = fields


class ParentProfileResource(resources.ModelResource):
    class Meta:
        model = ParentProfile
        fields = ('id', 'user', 'phone_number', 'school')
        export_order = fields


class StreamResource(resources.ModelResource):
    class Meta:
        model = Stream
        fields = ('id', 'name', 'school')
        export_order = fields


class ClassLevelResource(resources.ModelResource):
    class Meta:
        model = ClassLevel
        fields = ('id', 'name', 'school', 'class_teacher')
        export_order = fields


class StudentProfileResource(resources.ModelResource):
    class Meta:
        model = StudentProfile
        fields = ('id', 'user', 'admission_number', 'gender', 'class_level', 'stream', 'school')
        export_order = fields


class SubjectResource(resources.ModelResource):
    class Meta:
        model = Subject
        fields = ('id', 'name', 'code', 'school')
        export_order = fields


class MarkResource(resources.ModelResource):
    class Meta:
        model = Mark
        fields = ('id', 'student', 'subject', 'teacher', 'term', 'exam', 'mid_term', 'end_term', 'school')
        export_order = fields


# ============================================================
# Admin Classes with Import/Export
# ============================================================

@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    resource_class = UserResource  # Use custom resource
    list_display = ('username', 'email', 'role', 'school', 'is_staff', 'is_active')
    list_filter = ('role', 'school', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('School & Role', {
            'fields': ('school', 'role'),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'school', 'role'),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure password is hashed when saving"""
        if not change and obj.password:
            # New user - hash password if not already hashed
            if not obj.password.startswith('pbkdf2_sha256'):
                obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(School)
class SchoolAdmin(ImportExportModelAdmin):
    resource_class = SchoolResource
    list_display = ('name', 'code', 'phone', 'email')
    search_fields = ('name', 'code')

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(ImportExportModelAdmin):
    resource_class = EmployeeProfileResource
    list_display = ('user', 'staff_id', 'school', 'hire_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'staff_id')
    list_filter = ('school',)


@admin.register(ParentProfile)
class ParentProfileAdmin(ImportExportModelAdmin):
    resource_class = ParentProfileResource
    list_display = ('user', 'school', 'phone_number')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('school',)


@admin.register(Stream)
class StreamAdmin(ImportExportModelAdmin):
    resource_class = StreamResource
    list_display = ('name', 'school')
    search_fields = ('name',)
    list_filter = ('school',)


@admin.register(ClassLevel)
class ClassLevelAdmin(ImportExportModelAdmin):
    resource_class = ClassLevelResource
    list_display = ('name', 'school', 'class_teacher')
    search_fields = ('name',)
    list_filter = ('school',)


@admin.register(StudentProfile)
class StudentProfileAdmin(ImportExportModelAdmin):
    resource_class = StudentProfileResource
    list_display = ('user', 'admission_number', 'school', 'class_level', 'stream')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'admission_number')
    list_filter = ('school', 'class_level', 'stream')
    filter_horizontal = ('parent',)


@admin.register(Subject)
class SubjectAdmin(ImportExportModelAdmin):
    resource_class = SubjectResource
    list_display = ('name', 'code', 'school')
    search_fields = ('name', 'code')
    list_filter = ('school',)


@admin.register(Mark)
class MarkAdmin(ImportExportModelAdmin):
    resource_class = MarkResource
    list_display = ('student', 'subject', 'term', 'exam', 'mid_term', 'end_term', 'total_score', 'grade')
    search_fields = ('student__user__username', 'student__user__first_name', 'student__user__last_name')
    list_filter = ('school', 'term', 'exam', 'subject')
    list_editable = ('mid_term', 'end_term')


@admin.register(Timetable)
class TimetableAdmin(ImportExportModelAdmin):
    list_display = ('class_level', 'stream', 'subject', 'teacher', 'day', 'start_time', 'end_time')
    list_filter = ('school', 'day', 'class_level', 'stream')
    search_fields = ('subject__name', 'teacher__user__first_name', 'teacher__user__last_name')


# Customize admin site header
admin.site.site_header = "School Management System Admin"
admin.site.site_title = "SchoolMS Admin"
admin.site.index_title = "Welcome to SchoolMS Administration"