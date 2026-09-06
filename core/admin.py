from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin import AdminSite as _AdminSite
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Avg, ExpressionWrapper, F, FloatField
from django.contrib import messages
from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark, Timetable,
    SCOPED_ROLES,
)
from .resources import (
    SchoolResource, UserResource, EmployeeProfileResource,
    ParentProfileResource, StreamResource, ClassLevelResource,
    StudentProfileResource, SubjectResource, MarkResource,
    TimetableResource,
)


# ── Branding ───────────────────────────────────────────────────────────────
admin.site.site_header = '🏫 SchoolMS Administration'
admin.site.site_title  = 'SchoolMS Admin'
admin.site.index_title = 'Dashboard'


# ── Dashboard stats ────────────────────────────────────────────────────────
_original_index = _AdminSite.index


def _patched_index(self, request, extra_context=None):
    extra_context = extra_context or {}
    school = getattr(request.user, 'school', None)
    is_scoped = (
        not request.user.is_superuser
        and getattr(request.user, 'role', None) in SCOPED_ROLES
        and school
    )

    mark_qs    = Mark.objects.filter(school=school)            if is_scoped else Mark.objects.all()
    student_qs = StudentProfile.objects.filter(school=school)  if is_scoped else StudentProfile.objects.all()
    staff_qs   = EmployeeProfile.objects.filter(school=school) if is_scoped else EmployeeProfile.objects.all()
    subject_qs = Subject.objects.filter(school=school)         if is_scoped else Subject.objects.all()
    school_qs  = School.objects.filter(pk=school.pk)           if is_scoped else School.objects.all()

    avg = mark_qs.annotate(
        total=ExpressionWrapper(F('mid_term') + F('end_term'), output_field=FloatField())
    ).aggregate(a=Avg('total'))['a']

    extra_context.update({
        'school_count':  school_qs.count(),
        'student_count': student_qs.count(),
        'staff_count':   staff_qs.count(),
        'subject_count': subject_qs.count(),
        'mark_count':    mark_qs.count(),
        'avg_score':     f"{avg:.1f}" if avg is not None else '—',
    })
    return _original_index(self, request, extra_context)


_AdminSite.index = _patched_index


# ── Role badge colours ─────────────────────────────────────────────────────

ROLE_COLORS = {
    'system_admin':   '#7c3aed',
    'school_admin':   '#1d4ed8',
    'headteacher':    '#1d4ed8',
    'dos':            '#0e7490',
    'bursar':         '#b45309',
    'nurse':          '#be185d',
    'librarian':      '#7c3aed',
    'lab_technician': '#065f46',
    'class_teacher':  '#0369a1',
    'teacher':        '#0369a1',
    'parent':         '#374151',
    'student':        '#374151',
}


# ── Auto School Admin ──────────────────────────────────────────────────────

class AutoSchoolAdmin(ImportExportModelAdmin):
    """
    Base admin class that auto-assigns school for all models.
    Aligns with models.py validation rules.
    """
    
    def save_model(self, request, obj, form, change):
        """Auto-assign school from user's profile"""
        if hasattr(obj, "school"):
            # For scoped users, auto-assign from user
            if request.user.school:
                obj.school = request.user.school
                obj.school_id = request.user.school.id
            else:
                from .models import School
                first_school = School.objects.first()
                if first_school:
                    obj.school = first_school
                    obj.school_id = first_school.id
                else:
                    messages.error(request, "No school exists. Please create one first.")
                    return
        
        super().save_model(request, obj, form, change)


# ── School Scoped Mixin ──────────────────────────────────────────────────

class SchoolScopedMixin:
    """
    Restrict records to user's school.
    Aligns with SCOPED_ROLES from models.py.
    """

    school_field = "school"

    def _is_scoped(self, request):
        """Check if user should be scoped - excludes system_admin"""
        return (
            request.user.is_authenticated
            and not request.user.is_superuser
            and request.user.role != 'system_admin'
            and getattr(request.user, "role", None) in SCOPED_ROLES
        )

    def _user_school(self, request):
        return getattr(request.user, "school", None)

    def get_queryset(self, request):
        """Restrict list views to user's school"""
        qs = super().get_queryset(request)

        if self._is_scoped(request):
            school = self._user_school(request)

            if school:
                if hasattr(self.model, 'school'):
                    qs = qs.filter(school=school)
                elif self.model == User:
                    qs = qs.filter(school=school)
                else:
                    qs = qs.none()
            else:
                qs = qs.none()

        return qs

    def get_fields(self, request, obj=None):
        """Remove school field from forms for scoped users"""
        fields = list(super().get_fields(request, obj))

        if self._is_scoped(request) and "school" in fields:
            # For UserAdmin, keep school field (we make it read-only)
            if hasattr(self, 'model') and self.model == User:
                pass
            else:
                fields.remove("school")

        return fields

    def get_readonly_fields(self, request, obj=None):
        """Make school readonly for scoped users"""
        readonly = list(super().get_readonly_fields(request, obj))
        
        if self._is_scoped(request) and obj and "school" not in readonly:
            readonly.append("school")
        
        return readonly

    def get_list_filter(self, request):
        """Remove school from list filters for scoped users"""
        filters = list(super().get_list_filter(request))
        
        if self._is_scoped(request) and "school" in filters:
            filters.remove("school")
        
        return filters

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        RESTRICT DROPDOWN CHOICES TO USER'S SCHOOL ONLY!
        Aligns with models.py validation.
        """
        school = self._user_school(request)

        if self._is_scoped(request) and school:
            # Handle User dropdown - hide system_admin and other schools
            if db_field.related_model == User:
                kwargs['queryset'] = User.objects.filter(
                    school=school
                ).exclude(
                    role='system_admin'
                ).exclude(
                    is_superuser=True
                )
            
            # Handle EmployeeProfile
            elif db_field.related_model == EmployeeProfile:
                kwargs['queryset'] = EmployeeProfile.objects.filter(school=school)
            
            # Handle ParentProfile
            elif db_field.related_model == ParentProfile:
                kwargs['queryset'] = ParentProfile.objects.filter(school=school)
            
            # Handle StudentProfile
            elif db_field.related_model == StudentProfile:
                kwargs['queryset'] = StudentProfile.objects.filter(school=school)
            
            # Map other models
            mapping = {
                School:          School.objects.filter(pk=school.pk),
                StudentProfile:  StudentProfile.objects.filter(school=school),
                ClassLevel:      ClassLevel.objects.filter(school=school),
                Stream:          Stream.objects.filter(school=school),
                Subject:         Subject.objects.filter(school=school),
                Mark:            Mark.objects.filter(school=school),
                Timetable:       Timetable.objects.filter(school=school),
            }
            
            if db_field.related_model in mapping:
                kwargs['queryset'] = mapping[db_field.related_model]
            elif hasattr(db_field.related_model, 'school'):
                kwargs['queryset'] = db_field.related_model.objects.filter(school=school)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Restrict many-to-many choices to user's school"""
        school = self._user_school(request)
        
        if self._is_scoped(request) and school:
            if db_field.related_model == ParentProfile:
                kwargs['queryset'] = ParentProfile.objects.filter(school=school)
            elif hasattr(db_field.related_model, 'school'):
                kwargs['queryset'] = db_field.related_model.objects.filter(school=school)
        
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_search_results(self, request, queryset, search_term):
        """Restrict search results to user's school"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        if self._is_scoped(request):
            school = self._user_school(request)
            if school:
                if hasattr(queryset.model, 'school'):
                    queryset = queryset.filter(school=school)
                elif queryset.model == User:
                    queryset = queryset.filter(school=school)
        
        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        """Auto-assign school from user's profile"""
        if hasattr(obj, "school"):
            if request.user.school:
                obj.school = request.user.school
                obj.school_id = request.user.school.id
            else:
                from .models import School
                first_school = School.objects.first()
                if first_school:
                    obj.school = first_school
                    obj.school_id = first_school.id
                else:
                    messages.error(request, "No school exists. Please create one first.")
                    return
        
        super().save_model(request, obj, form, change)


# ── School Scoped Inline ──────────────────────────────────────────────────

class SchoolScopedInline(admin.StackedInline):
    """Inline version with full school isolation"""

    def _is_scoped(self, request):
        return (
            request.user.is_authenticated
            and not request.user.is_superuser
            and request.user.role != 'system_admin'
            and getattr(request.user, "role", None) in SCOPED_ROLES
        )

    def _user_school(self, request):
        return getattr(request.user, "school", None)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if self._is_scoped(request):
            school = self._user_school(request)
            if school and hasattr(self.model, 'school'):
                qs = qs.filter(school=school)

        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        school = self._user_school(request)

        if self._is_scoped(request) and school:
            if db_field.related_model == User:
                kwargs['queryset'] = User.objects.filter(
                    school=school
                ).exclude(
                    role='system_admin'
                ).exclude(
                    is_superuser=True
                )
            
            elif db_field.related_model == EmployeeProfile:
                kwargs['queryset'] = EmployeeProfile.objects.filter(school=school)
            
            elif db_field.related_model == ParentProfile:
                kwargs['queryset'] = ParentProfile.objects.filter(school=school)
            
            elif db_field.related_model == StudentProfile:
                kwargs['queryset'] = StudentProfile.objects.filter(school=school)
            
            mapping = {
                ClassLevel:      ClassLevel.objects.filter(school=school),
                Stream:          Stream.objects.filter(school=school),
                Subject:         Subject.objects.filter(school=school),
                StudentProfile:  StudentProfile.objects.filter(school=school),
            }
            if db_field.related_model in mapping:
                kwargs['queryset'] = mapping[db_field.related_model]

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "school"):
            if request.user.school:
                obj.school = request.user.school
                obj.school_id = request.user.school.id
            else:
                from .models import School
                first_school = School.objects.first()
                if first_school:
                    obj.school = first_school
                    obj.school_id = first_school.id
                else:
                    return

        super().save_model(request, obj, form, change)


# ── Inlines ────────────────────────────────────────────────────────────────

class EmployeeProfileInline(SchoolScopedInline):
    model               = EmployeeProfile
    can_delete          = False
    verbose_name_plural = 'Employee Profile'
    fk_name             = 'user'
    extra               = 0
    fields              = ('staff_id', 'hire_date')


class ParentProfileInline(SchoolScopedInline):
    model               = ParentProfile
    can_delete          = False
    verbose_name_plural = 'Parent Profile'
    fk_name             = 'user'
    extra               = 0
    fields              = ('phone_number',)


class StudentProfileInline(SchoolScopedInline):
    model               = StudentProfile
    can_delete          = False
    verbose_name_plural = 'Student Profile'
    fk_name             = 'user'
    extra               = 0
    fields              = (
        'admission_number', 'gender',
        'class_level', 'stream', 'passport_photo',
    )


# ── School Admin ──────────────────────────────────────────────────────────

@admin.register(School)
class SchoolAdmin(ImportExportModelAdmin):
    resource_class = SchoolResource
    list_display     = ('name', 'code', 'phone', 'email')
    search_fields    = ('name', 'code')


# ── User Admin ────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(ImportExportModelAdmin, SchoolScopedMixin, BaseUserAdmin):

    resource_class = UserResource
    list_display     = ('username', 'full_name', 'role_badge', 'school', 'is_active', 'date_joined')
    list_filter      = ('role', 'school', 'is_active')
    search_fields    = ('username', 'email', 'first_name', 'last_name')
    ordering         = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('School & Role', {'fields': ('school', 'role')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('username', 'password1', 'password2', 'school', 'role'),
        }),
    )

    def get_fields(self, request, obj=None):
        return super(SchoolScopedMixin, self).get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        return super(SchoolScopedMixin, self).get_readonly_fields(request, obj)

    def get_queryset(self, request):
        qs = super(ImportExportModelAdmin, self).get_queryset(request)
        if self._is_scoped(request):
            school = self._user_school(request)
            if school:
                qs = qs.filter(school=school).exclude(role='system_admin').exclude(is_superuser=True)
            else:
                qs = qs.none()
        return qs

    def save_model(self, request, obj, form, change):
        # Prevent scoped users from creating system_admin
        if self._is_scoped(request) and obj.role == 'system_admin':
            messages.error(request, "You cannot create a System Admin user.")
            return
        
        # Auto-correct system_admin: no school, superuser=True
        if obj.role == 'system_admin':
            obj.school = None
            obj.school_id = None
            obj.is_superuser = True
            obj.is_staff = True
        else:
            if self._is_scoped(request):
                obj.school = request.user.school
                obj.school_id = request.user.school.id
            obj.is_superuser = False
            obj.is_staff = True
            
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Hide system_admin role from scoped users
        if self._is_scoped(request):
            role = form.base_fields.get('role')
            if role:
                role.choices = [x for x in role.choices if x[0] != 'system_admin']
            
            # Restrict school field to user's school only
            school_field = form.base_fields.get('school')
            if school_field:
                school_field.queryset = School.objects.filter(pk=request.user.school.pk)
                school_field.initial = request.user.school
                school_field.widget.attrs['readonly'] = True
        
        # If editing a system_admin, make school field invisible
        if obj and obj.role == 'system_admin':
            school_field = form.base_fields.get('school')
            if school_field:
                school_field.queryset = School.objects.none()
                school_field.initial = None
                school_field.widget.attrs['readonly'] = True
                school_field.required = False
        
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if self._is_scoped(request) and db_field.name == 'school':
            kwargs['queryset'] = School.objects.filter(pk=request.user.school.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.get_full_name() or obj.username

    @admin.display(description='Role')
    def role_badge(self, obj):
        color = ROLE_COLORS.get(obj.role, '#374151')
        return format_html(
            '<span style="background:{};color:white;padding:4px 10px;'
            'border-radius:30px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_role_display(),
        )


# ── Stream Admin ───────────────────────────────────────────────────────────

@admin.register(Stream)
class StreamAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class = StreamResource
    list_display   = ('name', 'school', 'student_count')
    list_filter    = ('school',)
    search_fields  = ('name',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return StudentProfile.objects.filter(stream=obj).count()


# ── ClassLevel Admin ───────────────────────────────────────────────────────

@admin.register(ClassLevel)
class ClassLevelAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class     = ClassLevelResource
    list_display       = ('name', 'school', 'class_teacher', 'student_count')
    list_filter        = ('school',)
    search_fields      = ('name',)
    autocomplete_fields = ('class_teacher',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return StudentProfile.objects.filter(class_level=obj).count()


# ── Subject Admin ──────────────────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class = SubjectResource
    list_display   = ('name', 'code', 'school', 'avg_total')
    list_filter    = ('school',)
    search_fields  = ('name', 'code')
    ordering       = ('school', 'name')

    @admin.display(description='Avg Total')
    def avg_total(self, obj):
        avg = Mark.objects.filter(subject=obj).annotate(
            total=ExpressionWrapper(F('mid_term') + F('end_term'), output_field=FloatField())
        ).aggregate(a=Avg('total'))['a']
        if avg is None:
            return '—'
        color = '#166534' if avg >= 50 else '#991b1b'
        return format_html('<strong style="color:{}">{}</strong>', color, f"{avg:.1f}")


# ── EmployeeProfile Admin ──────────────────────────────────────────────────

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class = EmployeeProfileResource
    list_display   = ('full_name', 'role_badge', 'school', 'staff_id', 'hire_date')
    list_filter    = ('school', 'user__role')
    search_fields  = ('user__username', 'user__first_name', 'user__last_name', 'staff_id')
    ordering       = ('school', 'staff_id')

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Role')
    def role_badge(self, obj):
        color = ROLE_COLORS.get(obj.user.role, '#374151')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:99px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.user.get_role_display(),
        )


# ── ParentProfile Admin ────────────────────────────────────────────────────

@admin.register(ParentProfile)
class ParentProfileAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class = ParentProfileResource
    list_display   = ('full_name', 'school', 'phone_number', 'children_count')
    list_filter    = ('school',)
    search_fields  = ('user__username', 'user__first_name', 'user__last_name', 'phone_number')

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Children')
    def children_count(self, obj):
        return obj.children.count()


# ── StudentProfile Admin ───────────────────────────────────────────────────

@admin.register(StudentProfile)
class StudentProfileAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class    = StudentProfileResource
    list_display      = (
        'full_name', 'admission_number', 'school',
        'class_level', 'stream', 'gender_badge', 'marks_count',
    )
    list_filter       = ('school', 'class_level', 'stream', 'gender')
    search_fields     = ('user__username', 'user__first_name', 'user__last_name', 'admission_number')
    filter_horizontal = ('parent',)
    ordering          = ('school', 'class_level', 'stream', 'user__first_name')
    list_per_page     = 30
    readonly_fields   = ('passport_preview',)

    fieldsets = (
        ('Personal', {
            'fields': ('user', 'admission_number', 'gender', 'passport_photo', 'passport_preview'),
        }),
        ('Academic', {
            'fields': ('class_level', 'stream'),
        }),
        ('Parents', {
            'fields': ('parent',),
        }),
    )

    # ADD THIS METHOD TO FIX THE ISSUE
    def save_model(self, request, obj, form, change):
        """Override to ensure school is always set"""
        # Set school from user if not already set
        if not obj.school_id:
            if request.user.school:
                obj.school = request.user.school
                obj.school_id = request.user.school.id
            elif request.user.is_superuser:
                # For superusers, try to get school from the user object
                if obj.user and obj.user.school:
                    obj.school = obj.user.school
                    obj.school_id = obj.user.school.id
                else:
                    # Fallback to first school
                    from .models import School
                    first_school = School.objects.first()
                    if first_school:
                        obj.school = first_school
                        obj.school_id = first_school.id
        
        super().save_model(request, obj, form, change)

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Gender')
    def gender_badge(self, obj):
        color = '#1d4ed8' if obj.gender == 'M' else '#be185d'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:99px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_gender_display(),
        )

    @admin.display(description='Marks')
    def marks_count(self, obj):
        count = Mark.objects.filter(student=obj).count()
        url   = reverse('admin:core_mark_changelist') + f'?student__user__username={obj.user.username}'
        return format_html('<a href="{}">{} entries</a>', url, count)

    @admin.display(description='Current Photo')
    def passport_preview(self, obj):
        if obj.passport_photo:
            return format_html(
                '<img src="{}" style="height:80px;border-radius:4px;" />',
                obj.passport_photo.url,
            )
        return '—'


# ── Mark Admin ─────────────────────────────────────────────────────────────

@admin.register(Mark)
class MarkAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class = MarkResource
    list_display   = (
        'student_name', 'subject', 'term', 'exam',
        'mid_term', 'end_term', 'total_display', 'grade_badge',
        'teacher_name', 'school',
    )
    list_filter    = ('school', 'term', 'exam', 'subject', 'student__class_level', 'student__stream')
    search_fields  = (
        'student__user__first_name', 'student__user__last_name',
        'student__admission_number', 'subject__name',
    )
    ordering       = ('school', 'term', 'exam', 'student__user__first_name')
    list_per_page  = 40
    list_editable  = ('mid_term', 'end_term')

    @admin.display(description='Student')
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username

    @admin.display(description='Total')
    def total_display(self, obj):
        return f"{obj.total_score:.1f}"

    @admin.display(description='Teacher')
    def teacher_name(self, obj):
        return obj.teacher.user.get_full_name() if obj.teacher else '—'

    @admin.display(description='Grade')
    def grade_badge(self, obj):
        colors = {'A': '#166534', 'B': '#1d4ed8', 'C': '#374151', 'F': '#991b1b'}
        g = obj.grade
        return format_html('<strong style="color:{}">{}</strong>', colors.get(g, '#374151'), g)


# ── Timetable Admin ────────────────────────────────────────────────────────

@admin.register(Timetable)
class TimetableAdmin(AutoSchoolAdmin, SchoolScopedMixin):
    resource_class = TimetableResource
    list_display   = ('school', 'class_level', 'stream', 'subject', 'teacher', 'day', 'start_time', 'end_time', 'room')
    list_filter    = ('school', 'day', 'class_level', 'stream', 'subject')
    search_fields  = ('subject__name', 'teacher__user__first_name', 'teacher__user__last_name', 'room')
    ordering       = ('school', 'class_level', 'day', 'start_time')

    fieldsets = (
        (None, {
            'fields': ('class_level', 'stream', 'subject', 'teacher', 'day', 'start_time', 'end_time', 'room'),
        }),
    )