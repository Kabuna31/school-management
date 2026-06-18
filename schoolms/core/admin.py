from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import (
    School, User, EmployeeProfile, ParentProfile,
    Stream, ClassLevel, StudentProfile, Subject, Mark
)

# ── Branding ───────────────────────────────────────────────────────────────
admin.site.site_header  = '🏫 SchoolMS Administration'
admin.site.site_title   = 'SchoolMS Admin'
admin.site.index_title  = 'Dashboard'


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


# ── User ───────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('username', 'full_name', 'role_badge', 'school', 'is_active', 'date_joined')
    list_filter   = ('role', 'school', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    list_per_page = 25

    fieldsets = BaseUserAdmin.fieldsets + (
        ('School & Role', {'fields': ('school', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('School & Role', {'fields': ('school', 'role')}),
    )

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.get_full_name() or '—'

    @admin.display(description='Role')
    def role_badge(self, obj):
        colors = {
            'system_admin':   '#7c3aed',
            'headteacher':    '#1d4ed8',
            'dos':            '#0369a1',
            'class_teacher':  '#0369a1',
            'teacher':        '#0369a1',
            'bursar':         '#b45309',
            'nurse':          '#be185d',
            'librarian':      '#047857',
            'lab_technician': '#047857',
            'parent':         '#374151',
            'student':        '#374151',
        }
        color = colors.get(obj.role, '#374151')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:99px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_role_display()
        )

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        staff_roles = {
            'system_admin', 'headteacher', 'bursar',
            'nurse', 'librarian', 'lab_technician', 'dos',
            'class_teacher', 'teacher'
        }
        if obj.role in staff_roles:
            return [EmployeeProfileInline]
        if obj.role == 'parent':
            return [ParentProfileInline]
        if obj.role == 'student':
            return [StudentProfileInline]
        return []


# ── School ─────────────────────────────────────────────────────────────────

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'student_count', 'teacher_count', 'created_at')
    search_fields = ('name', 'code')
    ordering      = ('name',)

    @admin.display(description='Students')
    def student_count(self, obj):
        count = StudentProfile.objects.filter(school=obj).count()
        return format_html('<strong>{}</strong>', count)

    @admin.display(description='Teachers')
    def teacher_count(self, obj):
        count = EmployeeProfile.objects.filter(school=obj).count()
        return format_html('<strong>{}</strong>', count)


# ── Stream ─────────────────────────────────────────────────────────────────

@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display  = ('name', 'school', 'student_count')
    list_filter   = ('school',)
    search_fields = ('name',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return StudentProfile.objects.filter(stream=obj).count()


# ── ClassLevel ─────────────────────────────────────────────────────────────

@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display      = ('name', 'school', 'class_teacher', 'student_count')
    list_filter       = ('school',)
    search_fields     = ('name',)
    autocomplete_fields = ('class_teacher',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return StudentProfile.objects.filter(class_level=obj).count()


# ── EmployeeProfile ────────────────────────────────────────────────────────

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'role_badge', 'school', 'staff_id', 'hire_date')
    list_filter   = ('school', 'user__role')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'staff_id')
    ordering      = ('school', 'staff_id')

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


# ── ParentProfile ──────────────────────────────────────────────────────────

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
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
class StudentProfileAdmin(admin.ModelAdmin):
    list_display    = ('full_name', 'admission_number', 'school', 'class_level', 'stream', 'gender_badge', 'marks_count')
    list_filter     = ('school', 'class_level', 'stream', 'gender')
    search_fields   = ('user__username', 'user__first_name', 'user__last_name', 'admission_number')
    filter_horizontal = ('parent',)
    ordering        = ('school', 'class_level', 'stream', 'user__first_name')
    list_per_page   = 30

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


# ── Subject ────────────────────────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'school', 'avg_score')
    list_filter   = ('school',)
    search_fields = ('name', 'code')
    ordering      = ('school', 'name')

    @admin.display(description='Avg Score')
    def avg_score(self, obj):
        avg = Mark.objects.filter(subject=obj).aggregate(a=Avg('score'))['a']
        if avg is None:
            return '—'
        color = '#166534' if avg >= 50 else '#991b1b'
        return format_html(
            '<strong style="color:{}">{:.1f}</strong>', color, avg
        )


# ── Mark ───────────────────────────────────────────────────────────────────

@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display   = ('student_name', 'subject', 'term', 'score_badge', 'teacher_name', 'school')
    list_filter    = ('school', 'term', 'subject', 'student__class_level', 'student__stream')
    search_fields  = (
        'student__user__first_name', 'student__user__last_name',
        'student__admission_number', 'subject__name',
    )
    ordering       = ('school', 'term', 'student__user__first_name')
    list_per_page  = 40
    list_editable  = ('score',)  # quick inline editing from list view

    # Override list_display to allow list_editable
    list_display   = ('student_name', 'subject', 'term', 'score', 'grade', 'teacher_name', 'school')

    @admin.display(description='Student')
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username

    @admin.display(description='Teacher')
    def teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.user.get_full_name() or obj.teacher.user.username
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
        return format_html(
            '<strong style="color:{}">{}</strong>', color, label
        )


# ── Custom Admin Site with stats on index ──────────────────────────────────

from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse
from django.db.models import Avg


class SchoolAdminSite(admin.AdminSite):
    site_header  = '🏫 SchoolMS Administration'
    site_title   = 'SchoolMS Admin'
    index_title  = 'Dashboard'

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        avg = Mark.objects.aggregate(a=Avg('score'))['a']

        extra_context.update({
            'school_count':  School.objects.count(),
            'student_count': StudentProfile.objects.count(),
            'staff_count':   EmployeeProfile.objects.count(),
            'subject_count': Subject.objects.count(),
            'mark_count':    Mark.objects.count(),
            'avg_score':     f"{avg:.1f}" if avg else '—',
        })
        return super().index(request, extra_context)
