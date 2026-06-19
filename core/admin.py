from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin
from .resources import UserResource
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark
)
from .resources import (
    SchoolResource, UserResource, EmployeeProfileResource,
    StreamResource, ClassLevelResource, StudentProfileResource,
    SubjectResource, MarkResource
)


# ── Branding ───────────────────────────────────────────────────────────────
admin.site.site_header = '🏫 SchoolMS Administration'
admin.site.site_title  = 'SchoolMS Admin'
admin.site.index_title = 'Dashboard'


# ── Scoping mixin ──────────────────────────────────────────────────────────

class SchoolScopedMixin:
    """
    Mixin that scopes every admin view to the logged-in user's school
    when the user is a headteacher.

    System admins (is_superuser or role=system_admin) see everything.
    Headteachers only see records that belong to their school.
    """

    school_field = 'school'   # FK path to School on the model

    def _is_scoped(self, request):
        """Return True if this user should be restricted to their school."""
        return (
            not request.user.is_superuser
            and getattr(request.user, 'role', None) == 'headteacher'
        )

    def _user_school(self, request):
        return getattr(request.user, 'school', None)

    # ── Queryset scoping ───────────────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self._is_scoped(request):
            school = self._user_school(request)
            if school:
                qs = qs.filter(**{self.school_field: school})
            else:
                qs = qs.none()
        return qs

    # ── FK dropdowns scoping ───────────────────────────────────────────────
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        school = self._user_school(request)
        if self._is_scoped(request) and school:
            if db_field.related_model == School:
                kwargs['queryset'] = School.objects.filter(pk=school.pk)
            elif db_field.related_model == User:
                kwargs['queryset'] = User.objects.filter(school=school)
            elif db_field.related_model == EmployeeProfile:
                kwargs['queryset'] = EmployeeProfile.objects.filter(school=school)
            elif db_field.related_model == StudentProfile:
                kwargs['queryset'] = StudentProfile.objects.filter(school=school)
            elif db_field.related_model == ClassLevel:
                kwargs['queryset'] = ClassLevel.objects.filter(school=school)
            elif db_field.related_model == Stream:
                kwargs['queryset'] = Stream.objects.filter(school=school)
            elif db_field.related_model == Subject:
                kwargs['queryset'] = Subject.objects.filter(school=school)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ── M2M dropdowns scoping ──────────────────────────────────────────────
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        school = self._user_school(request)
        if self._is_scoped(request) and school:
            if db_field.related_model == ParentProfile:
                kwargs['queryset'] = ParentProfile.objects.filter(school=school)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    # ── Autocomplete scoping ───────────────────────────────────────────────
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if self._is_scoped(request):
            school = self._user_school(request)
            if school:
                queryset = queryset.filter(**{self.school_field: school})
        return queryset, use_distinct

    # ── Pre-populate school on new records ─────────────────────────────────
    def save_model(self, request, obj, form, change):
        if self._is_scoped(request) and not change:
            school = self._user_school(request)
            if school and hasattr(obj, 'school'):
                obj.school = school
        super().save_model(request, obj, form, change)

    # ── Hide school field for headteachers (it's always theirs) ───────────
    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if self._is_scoped(request) and 'school' in fields:
            fields.remove('school')
        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if self._is_scoped(request):
            # Show school as read-only info rather than hiding entirely
            if 'school' not in readonly:
                readonly.append('school')
        return readonly


# ── Inlines ────────────────────────────────────────────────────────────────

class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    can_delete = False
    verbose_name_plural = 'Employee Profile'
    fk_name = 'user'
    extra = 0
    fields = ('school', 'staff_id', 'hire_date')


class ParentProfileInline(admin.StackedInline):
    model = ParentProfile
    can_delete = False
    verbose_name_plural = 'Parent Profile'
    fk_name = 'user'
    extra = 0
    fields = ('school', 'phone_number')


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'
    extra = 0
    fields = ('school', 'admission_number', 'gender', 'class_level', 'stream')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        school = getattr(request.user, 'school', None)
        is_scoped = (
            not request.user.is_superuser
            and getattr(request.user, 'role', None) == 'headteacher'
            and school
        )
        if is_scoped:
            if db_field.related_model == ClassLevel:
                kwargs['queryset'] = ClassLevel.objects.filter(school=school)
            elif db_field.related_model == Stream:
                kwargs['queryset'] = Stream.objects.filter(school=school)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ── Schools ───────────────────────────────────────────────────────────────────
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# ── User ───────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(
    ImportExportModelAdmin,
    SchoolScopedMixin,
    BaseUserAdmin
):

    resource_class = UserResource
    school_field = "school"

    list_display = (
        "username",
        "full_name",
        "role_badge",
        "school",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "school",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "School & Role",
            {
                "fields": ("school", "role")
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "School & Role",
            {
                "fields": ("school", "role")
            },
        ),
    )

    # ── FIX 1: clean queryset (DO NOT hide system_admin)
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if self._is_scoped(request):
            school = self._user_school(request)

            qs = qs.filter(school=school)

        return qs

    # ── FIX 2: proper role ↔ superuser sync
    def save_model(self, request, obj, form, change):

        if self._is_scoped(request):
            obj.school = request.user.school

            # SYSTEM ADMIN RULE
            if obj.role == "system_admin":
                obj.is_superuser = True
                obj.is_staff = True

            # ALL OTHERS
            else:
                obj.is_superuser = False

        super().save_model(request, obj, form, change)

    # ── FIX 3: restrict school field safely
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        school = self._user_school(request)

        if self._is_scoped(request):
            if db_field.name == "school":
                kwargs["queryset"] = School.objects.filter(pk=school.pk)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Name")
    def full_name(self, obj):
        return obj.get_full_name() or obj.username

    @admin.display(description="Role")
    def role_badge(self, obj):

        colors = {
            "system_admin": "#7c3aed",
            "headteacher": "#1d4ed8",
            "teacher": "#0369a1",
            "student": "#374151",
            "parent": "#374151",
        }

        return format_html(
            '<span style="background:{};color:white;padding:4px 10px;border-radius:30px;">{}</span>',
            colors.get(obj.role, "#374151"),
            obj.get_role_display(),
        )

# ── Stream ─────────────────────────────────────────────────────────────────

@admin.register(Stream)
class StreamAdmin(SchoolScopedMixin, ImportExportModelAdmin):
    resource_classes = [StreamResource]
    list_display     = ('name', 'school', 'student_count')
    list_filter      = ('school',)
    search_fields    = ('name',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return StudentProfile.objects.filter(stream=obj).count()

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._is_scoped(request) and 'school' in filters:
            filters.remove('school')
        return filters


# ── ClassLevel ─────────────────────────────────────────────────────────────

@admin.register(ClassLevel)
class ClassLevelAdmin(SchoolScopedMixin, ImportExportModelAdmin):
    resource_classes    = [ClassLevelResource]
    list_display        = ('name', 'school', 'class_teacher', 'student_count')
    list_filter         = ('school',)
    search_fields       = ('name',)
    autocomplete_fields = ('class_teacher',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return StudentProfile.objects.filter(class_level=obj).count()

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._is_scoped(request) and 'school' in filters:
            filters.remove('school')
        return filters


# ── EmployeeProfile ────────────────────────────────────────────────────────

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(SchoolScopedMixin, ImportExportModelAdmin):
    resource_classes = [EmployeeProfileResource]
    list_display     = ('full_name', 'role_badge', 'school', 'staff_id', 'hire_date')
    list_filter      = ('school', 'user__role')
    search_fields    = ('user__username', 'user__first_name', 'user__last_name', 'staff_id')
    ordering         = ('school', 'staff_id')

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Role')
    def role_badge(self, obj):
        return format_html(
            '<span style="background:#0369a1;color:#fff;padding:2px 8px;'
            'border-radius:99px;font-size:11px;font-weight:600;">{}</span>',
            obj.user.get_role_display()
        )

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._is_scoped(request) and 'school' in filters:
            filters.remove('school')
        return filters


# ── ParentProfile ──────────────────────────────────────────────────────────

@admin.register(ParentProfile)
class ParentProfileAdmin(SchoolScopedMixin, admin.ModelAdmin):
    list_display  = ('full_name', 'school', 'phone_number', 'children_count')
    list_filter   = ('school',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone_number')

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Children')
    def children_count(self, obj):
        return obj.children.count()


# ── StudentProfile ─────────────────────────────────────────────────────────

@admin.register(StudentProfile)
class StudentProfileAdmin(SchoolScopedMixin, ImportExportModelAdmin):
    resource_classes  = [StudentProfileResource]
    list_display      = ('full_name', 'admission_number', 'school', 'class_level', 'stream', 'gender_badge', 'marks_count')
    list_filter       = ('school', 'class_level', 'stream', 'gender')
    search_fields     = ('user__username', 'user__first_name', 'user__last_name', 'admission_number')
    filter_horizontal = ('parent',)
    ordering          = ('school', 'class_level', 'stream', 'user__first_name')
    list_per_page     = 30

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Gender')
    def gender_badge(self, obj):
        color = '#1d4ed8' if obj.gender == 'M' else '#be185d'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:99px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_gender_display()
        )

    @admin.display(description='Marks')
    def marks_count(self, obj):
        count = Mark.objects.filter(student=obj).count()
        url   = reverse('admin:core_mark_changelist') + f'?student__user__username={obj.user.username}'
        return format_html('<a href="{}">{} entries</a>', url, count)

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._is_scoped(request) and 'school' in filters:
            filters.remove('school')
        return filters


# ── Subject ────────────────────────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(SchoolScopedMixin, ImportExportModelAdmin):
    resource_classes = [SubjectResource]
    list_display     = ('name', 'code', 'school', 'avg_score')
    list_filter      = ('school',)
    search_fields    = ('name', 'code')
    ordering         = ('school', 'name')

    @admin.display(description='Avg Score')
    def avg_score(self, obj):
        avg = Mark.objects.filter(subject=obj).aggregate(a=Avg('score'))['a']
        if avg is None:
            return '—'
        avg_float = float(avg)
        color = '#166534' if avg_float >= 50 else '#991b1b'
        return format_html(
            '<strong style="color:{}">{}</strong>',
            color, f"{avg_float:.1f}"
        )

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._is_scoped(request) and 'school' in filters:
            filters.remove('school')
        return filters


# ── Mark ───────────────────────────────────────────────────────────────────

@admin.register(Mark)
class MarkAdmin(SchoolScopedMixin, ImportExportModelAdmin):
    resource_classes = [MarkResource]
    list_display     = ('student_name', 'subject', 'term', 'score', 'grade', 'teacher_name', 'school')
    list_filter      = ('school', 'exam', 'subject', 'student__class_level', 'student__stream')
    search_fields    = (
        'student__user__first_name', 'student__user__last_name',
        'student__admission_number', 'subject__name',
    )
    ordering         = ('school', 'exam', 'student__user__first_name')
    list_per_page    = 40
    list_editable    = ('score',)

    @admin.display(description='Student')
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username

    @admin.display(description='Teacher')
    def teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.user.get_full_name()
        return '—'

    @admin.display(description='Grade')
    def grade(self, obj):
        s = float(obj.score)
        if s >= 80:
            label, color = 'A', '#166534'
        elif s >= 65:
            label, color = 'B', '#1d4ed8'
        elif s >= 50:
            label, color = 'C', '#374151'
        else:
            label, color = 'F', '#991b1b'
        return format_html('<strong style="color:{}">{}</strong>', color, label)

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._is_scoped(request) and 'school' in filters:
            filters.remove('school')
        return filters


# ── Admin index stats ──────────────────────────────────────────────────────

_original_index = admin.site.__class__.index


def _patched_index(self, request, extra_context=None):
    extra_context = extra_context or {}
    school = getattr(request.user, 'school', None)
    is_scoped = (
        not request.user.is_superuser
        and getattr(request.user, 'role', None) == 'headteacher'
        and school
    )

    # Scope stats to school for headteachers
    mark_qs    = Mark.objects.filter(school=school)    if is_scoped else Mark.objects.all()
    student_qs = StudentProfile.objects.filter(school=school) if is_scoped else StudentProfile.objects.all()
    staff_qs   = EmployeeProfile.objects.filter(school=school) if is_scoped else EmployeeProfile.objects.all()
    subject_qs = Subject.objects.filter(school=school) if is_scoped else Subject.objects.all()
    school_qs  = School.objects.filter(pk=school.pk)  if is_scoped else School.objects.all()

    avg = mark_qs.aggregate(a=Avg('score'))['a']
    extra_context.update({
        'school_count':  school_qs.count(),
        'student_count': student_qs.count(),
        'staff_count':   staff_qs.count(),
        'subject_count': subject_qs.count(),
        'mark_count':    mark_qs.count(),
        'avg_score':     f"{float(avg):.1f}" if avg else '—',
    })
    return _original_index(self, request, extra_context)


admin.site.__class__.index = _patched_index
