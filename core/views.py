from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.response import TemplateResponse
from django.db.models import (
    Avg,
    Count,
    F,
    FloatField,
    ExpressionWrapper,
    Sum,
    Q,
)
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.views import LoginView
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db import IntegrityError

from .models import (
    School,
    User,
    EmployeeProfile,
    StudentProfile,
    ParentProfile,
    ClassLevel,
    Stream,
    Subject,
    Mark,
    ReportCard,
    ReportCardEntry,
    TERM_CHOICES,
    EXAM_CHOICES,
    MARK_MANAGE_ROLES,
    MARK_ENTRY_ROLES,
)
from .helpers import total_expr, mark_average, grade_letter, grade_points
from .reports import ReportGenerator


# ============================================================
# Fix Views (One-Time Fixes) — staff/superuser only
# ============================================================

@staff_member_required
def fix_school_view(request):
    """One-time view to fix school assignment for all users"""
    html = "<h1>Fixing School Assignment</h1>"

    school = School.objects.first()
    if not school:
        school = School.objects.create(
            name='St. Mary\'s School',
            code='SMS001',
            address='Kampala, Uganda',
            phone='+256700000000',
            email='info@stmarys.ug'
        )
        html += f"<p>✅ Created school: {school.name}</p>"
    else:
        html += f"<p>✅ Found school: {school.name}</p>"

    count = 0
    for user in User.objects.filter(school__isnull=True):
        if user.role == 'system_admin' or user.is_superuser:
            html += f"<p>⚠️ Skipped {user.username} (system_admin - should have no school)</p>"
            continue
        user.school = school
        user.save()
        count += 1
        html += f"<p>✅ Assigned {user.username} to {school.name}</p>"

    html += f"<p><strong>Total: {count} users assigned</strong></p>"
    html += '<p><a href="/admin/">Go to Admin Panel</a></p>'
    html += '<p><a href="/admin/core/classlevel/add/">Try Adding Class Level</a></p>'

    return HttpResponse(html)


@staff_member_required
def fix_admin_permissions_view(request):
    """One-time view to fix admin permissions"""
    User = get_user_model()
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        return HttpResponse("❌ Admin user not found!")

    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.is_active = True
    admin_user.role = 'system_admin'
    admin_user.school = None
    admin_user.school_id = None
    admin_user.user_permissions.set(Permission.objects.all())
    admin_user.save()

    html = f"""
    <h1>✅ Admin Permissions Fixed!</h1>
    <ul>
        <li>Username: {admin_user.username}</li>
        <li>Role: {admin_user.role}</li>
        <li>Superuser: {admin_user.is_superuser}</li>
        <li>Staff: {admin_user.is_staff}</li>
        <li>School: None (system_admin sees all schools)</li>
        <li>Permissions: {admin_user.user_permissions.count()}</li>
    </ul>
    <p><a href="/admin/">Go to Admin Panel</a></p>
    """
    return HttpResponse(html)


@staff_member_required
def set_username_as_password_view(request):
    """Set each user's password to their username"""
    User = get_user_model()
    users = User.objects.all()
    count = 0
    html = "<h1>Password Reset</h1><ul>"

    for user in users:
        user.password = make_password(user.username)
        user.save()
        count += 1
        html += f"<li>✅ {user.username} → password: <strong>{user.username}</strong></li>"

    html += f"</ul><p><strong>Total: {count} users updated</strong></p>"
    html += '<p><a href="/login/">Go to Login</a></p>'

    return HttpResponse(html)


@method_decorator(staff_member_required, name='dispatch')
class CreateAdminView(View):
    """One-time view to create admin user"""

    def get(self, request):
        User = get_user_model()

        if User.objects.filter(username='admin').exists():
            admin = User.objects.get(username='admin')
            admin.role = 'system_admin'
            admin.school = None
            admin.school_id = None
            admin.is_superuser = True
            admin.is_staff = True
            admin.save()
            return HttpResponse("""
                <h1>✅ Admin already exists!</h1>
                <p>Username: admin</p>
                <p>Role: system_admin</p>
                <p>School: None (sees all schools)</p>
                <p>Password: admin123456</p>
                <p><a href="/login/">Go to Login</a></p>
            """)

        admin = User.objects.create_superuser(
            username='admin',
            email='admin@school.com',
            password='admin123456'
        )
        admin.role = 'system_admin'
        admin.school = None
        admin.school_id = None
        admin.save()

        return HttpResponse("""
            <h1>✅ Admin created successfully!</h1>
            <p>Username: <strong>admin</strong></p>
            <p>Role: <strong>system_admin</strong></p>
            <p>School: <strong>None</strong> (sees all schools)</p>
            <p>Password: <strong>admin123456</strong></p>
            <p><a href="/login/">Go to Login</a></p>
        """)


# ============================================================
# Custom Login View
# ============================================================

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def form_valid(self, form):
        """
        If 'remember me' is not checked, expire the session when
        the browser closes (session cookie only, no persistent cookie).
        If checked, use the default SESSION_COOKIE_AGE (2 weeks).
        """
        remember = self.request.POST.get('remember_me')
        if not remember:
            self.request.session.set_expiry(0)
        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user
        role_map = {
            "system_admin":  "core:superuser_dashboard",
            "school_admin":  "core:schooladmin_dashboard",
            "headteacher":   "core:headteacher_dashboard",
            "dos":           "core:dos_dashboard",
            "teacher":       "core:teacher_dashboard",
            "class_teacher": "core:teacher_dashboard",
            "student":       "core:student_dashboard",
            "parent":        "core:parent_dashboard",
            "bursar":        "core:bursar_dashboard",
        }
        return reverse(role_map.get(user.role, "admin:index"))


# ============================================================
# Permission Mixins
# ============================================================

class RoleRequiredMixin:
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('core:login'))

        if not self.required_roles:
            return super().dispatch(request, *args, **kwargs)

        if request.user.is_superuser or request.user.role == 'system_admin':
            return super().dispatch(request, *args, **kwargs)

        if request.user.role not in self.required_roles:
            return HttpResponseForbidden(
                f"You don't have permission to access this page. "
                f"Required roles: {', '.join(self.required_roles)}"
            )
        return super().dispatch(request, *args, **kwargs)


class SchoolScopedMixin:
    """Mixin to ensure user only accesses their school's data"""

    def get_school(self):
        if hasattr(self.request.user, 'school'):
            return self.request.user.school
        return None

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'system_admin' or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        school = self.get_school()
        if not school:
            return HttpResponseForbidden(
                "You are not associated with a school. Please contact an administrator."
            )

        return super().dispatch(request, *args, **kwargs)


# ============================================================
# Role Redirect View
# ============================================================

class RoleRedirectView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('core:login')

        role_map = {
            "system_admin": "core:superuser_dashboard",
            "school_admin": "core:schooladmin_dashboard",
            "headteacher":  "core:headteacher_dashboard",
            "dos":          "core:dos_dashboard",
            "teacher":      "core:teacher_dashboard",
            "class_teacher":"core:teacher_dashboard",
            "student":      "core:student_dashboard",
            "parent":       "core:parent_dashboard",
            "bursar":       "core:bursar_dashboard",
        }

        return redirect(role_map.get(request.user.role, "admin:index"))


# ============================================================
# Dashboard Views
# ============================================================

class SuperuserDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "core/dashboard/superuser.html"
    required_roles = ['system_admin']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        marks = Mark.objects.select_related("student", "subject")
        ctx["school_count"] = School.objects.count()
        ctx["student_count"] = StudentProfile.objects.count()
        ctx["staff_count"] = EmployeeProfile.objects.count()
        ctx["subject_count"] = Subject.objects.count()
        ctx["mark_count"] = marks.count()
        ctx["avg_score"] = mark_average(marks)
        ctx["recent_marks"] = marks.order_by("-id")[:10]
        ctx["schools"] = School.objects.all()
        return ctx


class SchooladminDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/school_admin.html"
    required_roles = ['school_admin']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx
        marks = Mark.objects.filter(school=school)
        ctx["school"] = school
        ctx["student_count"] = StudentProfile.objects.filter(school=school).count()
        ctx["staff_count"] = EmployeeProfile.objects.filter(school=school).count()
        ctx["class_count"] = ClassLevel.objects.filter(school=school).count()
        ctx["subject_count"] = Subject.objects.filter(school=school).count()
        ctx["mark_count"] = marks.count()
        ctx["avg_score"] = mark_average(marks)
        ctx["recent_marks"] = marks.select_related("student", "subject", "teacher").order_by("-id")[:10]
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        return ctx


class HeadteacherDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/headteacher.html"
    required_roles = ['headteacher']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx
        marks = Mark.objects.filter(school=school)
        ctx["school"] = school
        ctx["student_count"] = StudentProfile.objects.filter(school=school).count()
        ctx["staff_count"] = EmployeeProfile.objects.filter(school=school).count()
        ctx["class_count"] = ClassLevel.objects.filter(school=school).count()
        ctx["subject_count"] = Subject.objects.filter(school=school).count()
        ctx["mark_count"] = marks.count()
        ctx["avg_score"] = mark_average(marks)
        ctx["recent_marks"] = marks.select_related("student", "subject", "teacher").order_by("-id")[:10]
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        return ctx


class DOSDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/dos.html"
    required_roles = ['dos']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx
        marks = Mark.objects.filter(school=school)
        ctx["school"] = school
        ctx["student_count"] = StudentProfile.objects.filter(school=school).count()
        ctx["staff_count"] = EmployeeProfile.objects.filter(school=school).count()
        ctx["class_count"] = ClassLevel.objects.filter(school=school).count()
        ctx["subject_count"] = Subject.objects.filter(school=school).count()
        ctx["mark_count"] = marks.count()
        ctx["avg_score"] = mark_average(marks)
        ctx["recent_marks"] = marks.select_related("student", "subject", "teacher").order_by("-id")[:10]
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        return ctx


class TeacherDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/teacher.html"
    required_roles = ['teacher', 'class_teacher']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx

        try:
            teacher = EmployeeProfile.objects.get(user=self.request.user)
            marks = Mark.objects.filter(school=school, teacher=teacher)
            ctx["my_marks_count"] = marks.count()
            ctx["my_avg_score"] = mark_average(marks)
        except EmployeeProfile.DoesNotExist:
            ctx["my_marks_count"] = 0
            ctx["my_avg_score"] = 0

        ctx["school"] = school
        ctx["student_count"] = StudentProfile.objects.filter(school=school).count()
        ctx["subject_count"] = Subject.objects.filter(school=school).count()
        return ctx


class BursarDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/bursar.html"
    required_roles = ['bursar']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx
        ctx["school"] = school
        ctx["student_count"] = StudentProfile.objects.filter(school=school).count()
        ctx["staff_count"] = EmployeeProfile.objects.filter(school=school).count()
        return ctx


class StudentDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/student.html"
    required_roles = ['student']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            student = StudentProfile.objects.select_related("class_level", "stream").get(
                user=self.request.user
            )
            marks = Mark.objects.filter(student=student).select_related("subject")
            ctx["student"] = student
            ctx["marks"] = marks
            ctx["avg_score"] = mark_average(marks)
            ctx["total_points"] = sum([m.grade_points for m in marks])
        except StudentProfile.DoesNotExist:
            ctx["student"] = None
            ctx["marks"] = []
            ctx["avg_score"] = 0
            ctx["total_points"] = 0
        return ctx


class ParentDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/dashboard/parent.html"
    required_roles = ['parent']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            parent = ParentProfile.objects.get(user=self.request.user)
            children = parent.children.all().prefetch_related("mark_set")
            rows = []
            for child in children:
                marks = Mark.objects.filter(student=child)
                rows.append({
                    "student": child,
                    "average": mark_average(marks),
                    "points": sum([m.grade_points for m in marks])
                })
            ctx["children"] = rows
            ctx["parent"] = parent
        except ParentProfile.DoesNotExist:
            ctx["children"] = []
            ctx["parent"] = None
        return ctx


# ============================================================
# Mark Entry Views
# ============================================================

class TeacherMarkEntryView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    template_name = "core/teacher_mark_entry.html"
    required_roles = MARK_ENTRY_ROLES

    def get(self, request):
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")

        selected_class = request.GET.get("class_level")
        selected_stream = request.GET.get("stream")
        selected_subject = request.GET.get("subject")
        selected_term = request.GET.get("term")
        selected_exam = request.GET.get("exam")

        students = StudentProfile.objects.none()
        existing_marks = {}

        if selected_class and selected_stream:
            students = StudentProfile.objects.filter(
                school=school,
                class_level=selected_class,
                stream_id=selected_stream
            ).select_related("user")

        if selected_subject and selected_term and selected_exam:
            marks = Mark.objects.filter(
                school=school,
                subject_id=selected_subject,
                term=selected_term,
                exam=selected_exam
            )
            for m in marks:
                existing_marks[m.student_id] = (
                    float(m.mid_term) if selected_exam == "Mid Term" else float(m.end_term)
                )

        context = {
            "classes": ClassLevel.objects.filter(school=school),
            "streams": Stream.objects.filter(school=school),
            "subjects": Subject.objects.filter(school=school),
            "terms": [t[0] for t in TERM_CHOICES],
            "exams": [e[0] for e in EXAM_CHOICES],
            "students": students,
            "existing_marks": existing_marks,
            "selected_class": selected_class,
            "selected_stream": selected_stream,
            "selected_subject": selected_subject,
            "selected_term": selected_term,
            "selected_exam": selected_exam,
            "success": request.GET.get("success"),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")

        try:
            teacher = EmployeeProfile.objects.get(user=request.user)
        except EmployeeProfile.DoesNotExist:
            teacher = None

        subject = request.POST.get("subject")
        term = request.POST.get("term")
        exam = request.POST.get("exam")
        class_level = request.POST.get("class_level")
        stream = request.POST.get("stream")

        if not all([subject, term, exam, class_level, stream]):
            messages.error(request, "Please select all required fields.")
            return redirect("core:teacher_mark_entry")

        students = StudentProfile.objects.filter(
            school=school,
            class_level=class_level,
            stream_id=stream
        )

        max_mark = 20 if exam == "Mid Term" else 80
        saved_count = 0

        for student in students:
            value = request.POST.get(f"student_{student.pk}")
            if not value:
                continue

            try:
                value = float(value)
                if value < 0 or value > max_mark:
                    continue

                try:
                    mark, created = Mark.objects.get_or_create(
                        school=school,
                        student=student,
                        subject_id=subject,
                        term=term,
                        exam=exam,
                        defaults={"teacher": teacher}
                    )
                except IntegrityError:
                    # Race condition: fetch the row that already exists
                    mark = Mark.objects.get(
                        school=school,
                        student=student,
                        subject_id=subject,
                        term=term,
                        exam=exam,
                    )

                if exam == "Mid Term":
                    mark.mid_term = value
                else:
                    mark.end_term = value

                if teacher:
                    mark.teacher = teacher

                mark.save()
                saved_count += 1

            except (ValueError, TypeError):
                continue

        if saved_count > 0:
            messages.success(request, f"Successfully saved {saved_count} marks!")
        else:
            messages.warning(request, "No marks were saved. Please check your input.")

        return redirect(reverse("core:teacher_mark_entry"))


class SchoolMarksView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/school_admin/marks.html"
    required_roles = MARK_MANAGE_ROLES

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx
        marks = Mark.objects.filter(school=school).select_related("student", "subject", "teacher")
        term = self.request.GET.get("term")
        if term:
            marks = marks.filter(term=term)
        ctx["marks"] = marks
        ctx["total_marks"] = marks.count()
        ctx["avg_score"] = mark_average(marks)
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        ctx["streams"] = Stream.objects.filter(school=school)
        ctx["subjects"] = Subject.objects.filter(school=school)
        ctx["terms"] = [t[0] for t in TERM_CHOICES]
        return ctx


class SchoolMarkEditView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    template_name = "core/school_admin/mark_edit.html"
    required_roles = MARK_MANAGE_ROLES

    def get(self, request, mark_id):
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")
        mark = get_object_or_404(Mark, pk=mark_id, school=school)
        return render(request, self.template_name, {"mark": mark})

    def post(self, request, mark_id):
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")
        mark = get_object_or_404(Mark, pk=mark_id, school=school)
        value = request.POST.get("mark_value")
        if not value:
            messages.error(request, "Please enter a value.")
            return redirect("core:school_mark_edit", mark_id=mark.pk)
        try:
            value = float(value)
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid number.")
            return redirect("core:school_mark_edit", mark_id=mark.pk)
        limit = 20 if mark.exam == "Mid Term" else 80
        if value < 0 or value > limit:
            messages.error(request, f"Value must be between 0 and {limit}.")
            return redirect("core:school_mark_edit", mark_id=mark.pk)
        if mark.exam == "Mid Term":
            mark.mid_term = value
        else:
            mark.end_term = value
        mark.save()
        messages.success(request, "Mark updated successfully!")
        return redirect("core:school_marks")


class DeleteMarkView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    required_roles = MARK_MANAGE_ROLES

    def post(self, request):
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")
        mark_id = request.POST.get("mark_id")
        if not mark_id:
            return redirect("core:school_marks")
        mark = Mark.objects.filter(pk=mark_id, school=school).first()
        if mark:
            mark.delete()
            messages.success(request, "Mark deleted successfully!")
        else:
            messages.error(request, "Mark not found.")
        return redirect("core:school_marks")


# ============================================================
# Student & Class Views
# ============================================================

class StudentProfileView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/student_profile.html"
    required_roles = ['school_admin', 'headteacher', 'dos', 'teacher', 'class_teacher', 'student', 'parent']

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        if not isinstance(response, TemplateResponse):
            return response

        student_id = kwargs.get('student_id')
        user = request.user

        if user.role == 'student':
            try:
                viewer_student = StudentProfile.objects.get(user=user)
                if viewer_student.pk != student_id:
                    return HttpResponseForbidden("You can only view your own profile.")
            except StudentProfile.DoesNotExist:
                return HttpResponseForbidden("Student profile not found.")

        if user.role == 'parent':
            try:
                parent = ParentProfile.objects.get(user=user)
                child_ids = list(parent.children.values_list('pk', flat=True))
                if student_id not in child_ids:
                    return HttpResponseForbidden("You can only view your children's profiles.")
            except ParentProfile.DoesNotExist:
                return HttpResponseForbidden("Parent profile not found.")

        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx

        student_id = self.kwargs.get('student_id')
        student = get_object_or_404(StudentProfile, pk=student_id, school=school)

        marks = Mark.objects.filter(student=student).select_related("subject", "teacher")
        marks_by_exam = {}
        for mark in marks:
            key = f"{mark.term} - {mark.exam}"
            marks_by_exam.setdefault(key, []).append(mark)

        ctx["student"] = student
        ctx["marks"] = marks
        ctx["marks_by_exam"] = marks_by_exam
        ctx["avg_score"] = mark_average(marks)
        ctx["total_points"] = sum([m.grade_points for m in marks])
        return ctx


class ClassMarksView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/class_marks.html"
    required_roles = ['school_admin', 'headteacher', 'dos', 'teacher', 'class_teacher']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        if not school:
            return ctx
        class_id = self.kwargs.get('class_id')
        class_level = get_object_or_404(ClassLevel, pk=class_id, school=school)
        students = StudentProfile.objects.filter(
            school=school, class_level=class_level
        ).select_related("user", "stream")
        student_ids = students.values_list('pk', flat=True)
        marks = Mark.objects.filter(
            student__in=student_ids
        ).select_related("student", "subject", "teacher")
        marks_by_student = {student.pk: [] for student in students}
        for mark in marks:
            marks_by_student[mark.student_id].append(mark)
        ctx["class_level"] = class_level
        ctx["students"] = students
        ctx["marks_by_student"] = marks_by_student
        ctx["terms"] = [t[0] for t in TERM_CHOICES]
        return ctx


# ============================================================
# Report Views
# ============================================================

class StudentReportView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/student_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher', 'student', 'parent']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student_id = self.kwargs.get('student_id')
        school = self.get_school()

        if not student_id and self.request.user.role == 'student':
            try:
                student = StudentProfile.objects.get(user=self.request.user)
                student_id = student.pk
            except StudentProfile.DoesNotExist:
                pass

        if not student_id and self.request.user.role == 'parent':
            try:
                parent = ParentProfile.objects.get(user=self.request.user)
                children = parent.children.all()
                if children.exists():
                    student_id = children.first().pk
            except ParentProfile.DoesNotExist:
                pass

        if student_id:
            report = ReportGenerator(school=school)
            ctx['report'] = report.student_performance_report(student_id)
            ctx['student'] = get_object_or_404(StudentProfile, pk=student_id)
            ctx['terms'] = [t[0] for t in TERM_CHOICES]
        return ctx


class ClassReportView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/class_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos']

    def get(self, request, *args, **kwargs):
        class_id = self.kwargs.get('class_id')
        if not class_id:
            messages.error(request, "No class selected.")
            return redirect('core:schooladmin_dashboard')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        class_id = self.kwargs.get('class_id')
        term = self.request.GET.get('term')
        exam = self.request.GET.get('exam')

        class_level = get_object_or_404(ClassLevel, pk=class_id, school=school)

        report = ReportGenerator(
            school=school,
            class_level=class_id,
            term=term,
            exam=exam
        )

        ctx['report'] = report.class_performance_report()
        ctx['class_level'] = class_level
        ctx['terms'] = [t[0] for t in TERM_CHOICES]
        ctx['exams'] = [e[0] for e in EXAM_CHOICES]
        ctx['selected_term'] = term
        ctx['selected_exam'] = exam
        return ctx


class TermReportView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/term_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        term = self.kwargs.get('term')
        exam = self.request.GET.get('exam')

        report = ReportGenerator(school=school, term=term, exam=exam)
        ctx['report'] = report.term_report()
        ctx['term'] = term
        ctx['exam'] = exam
        ctx['exams'] = [e[0] for e in EXAM_CHOICES]
        return ctx


class SubjectReportView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/subject_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        subject_id = self.kwargs.get('subject_id')
        term = self.request.GET.get('term')

        report = ReportGenerator(school=school, term=term)
        ctx['report'] = report.subject_performance_report(subject_id)
        ctx['subject'] = get_object_or_404(Subject, pk=subject_id, school=school) if subject_id else None
        ctx['terms'] = [t[0] for t in TERM_CHOICES]
        ctx['selected_term'] = term
        return ctx


class MarksheetView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/marksheet.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher', 'student', 'parent']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        student_id = self.kwargs.get('student_id')
        term = self.request.GET.get('term')

        if not student_id and self.request.user.role == 'student':
            try:
                student = StudentProfile.objects.get(user=self.request.user)
                student_id = student.pk
            except StudentProfile.DoesNotExist:
                pass

        report = ReportGenerator(school=school)
        marksheet = report.generate_marksheet(student_id, term)

        if not marksheet:
            ctx['error'] = "No marks found for this student."
        else:
            ctx['marksheet'] = marksheet
            ctx['student'] = get_object_or_404(StudentProfile, pk=student_id)
            ctx['term'] = term
            ctx['terms'] = [t[0] for t in TERM_CHOICES]
        return ctx


# ============================================================
# Performance Analytics View
# ============================================================

class PerformanceAnalyticsView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/analytics.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        term = self.request.GET.get('term')
        exam = self.request.GET.get('exam')

        marks = Mark.objects.filter(school=school)
        if term:
            marks = marks.filter(term=term)
        if exam:
            marks = marks.filter(exam=exam)

        total_marks = marks.count()
        avg_score = mark_average(marks)

        # grade is a @property (not a DB column) so we compute in Python.
        # Only fetch the two score fields to avoid loading full model instances.
        # Scale: A>=80, B>=70, C>=60, D>=50, E<50 (no F)
        grade_dist = {}
        if total_marks > 0:
            for mid, end in marks.values_list('mid_term', 'end_term'):
                t = float(mid or 0) + float(end or 0)
                if t >= 80:
                    g = 'A'
                elif t >= 70:
                    g = 'B'
                elif t >= 60:
                    g = 'C'
                elif t >= 50:
                    g = 'D'
                else:
                    g = 'E'
                entry = grade_dist.setdefault(g, {'count': 0, 'percentage': 0})
                entry['count'] += 1

            for g in grade_dist:
                grade_dist[g]['percentage'] = round(
                    grade_dist[g]['count'] / total_marks * 100, 1
                )

        ctx["total_marks"] = total_marks
        ctx["total_students"] = StudentProfile.objects.filter(school=school).count()
        ctx["avg_score"] = avg_score
        ctx["grade_distribution"] = grade_dist
        ctx["terms"] = [t[0] for t in TERM_CHOICES]
        ctx["exams"] = [e[0] for e in EXAM_CHOICES]
        ctx["selected_term"] = term
        ctx["selected_exam"] = exam
        return ctx


# ============================================================
# Download/Export Views
# ============================================================

class DownloadReportPDFView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher']

    def get(self, request, report_type, item_id, *args, **kwargs):
        school = self.get_school()
        html_string = self._get_report_html(request, report_type, item_id, school)

        if not html_string:
            return HttpResponse("Report not found", status=404)

        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration

            font_config = FontConfiguration()
            html = HTML(string=html_string)
            css = CSS(string='@page { size: A4; margin: 1cm; }')
            pdf = html.write_pdf(font_config=font_config, stylesheets=[css])

            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{item_id}.pdf"'
            return response

        except ImportError:
            response = HttpResponse(html_string, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{item_id}.html"'
            return response

    def _get_report_html(self, request, report_type, item_id, school):
        context = {}
        report = ReportGenerator(school=school)

        if report_type == 'student':
            context['report'] = report.student_performance_report(item_id)
            context['student'] = get_object_or_404(StudentProfile, pk=item_id)
            context['is_pdf'] = True
            template = 'core/reports/student_report.html'

        elif report_type == 'class':
            context['report'] = report.class_performance_report()
            context['class_level'] = get_object_or_404(ClassLevel, pk=item_id, school=school)
            context['school'] = school
            context['is_pdf'] = True
            template = 'core/reports/class_report.html'

        elif report_type == 'term':
            context['report'] = report.term_report()
            context['term'] = item_id
            context['exam'] = request.GET.get('exam')
            context['is_pdf'] = True
            template = 'core/reports/term_report.html'

        elif report_type == 'subject':
            context['report'] = report.subject_performance_report(item_id)
            context['subject'] = get_object_or_404(Subject, pk=item_id, school=school)
            context['is_pdf'] = True
            template = 'core/reports/subject_report.html'

        elif report_type == 'marksheet':
            marksheet = report.generate_marksheet(item_id, request.GET.get('term'))
            if not marksheet:
                return None
            context['marksheet'] = marksheet
            context['student'] = get_object_or_404(StudentProfile, pk=item_id)
            context['term'] = request.GET.get('term')
            context['is_pdf'] = True
            template = 'core/reports/marksheet.html'

        else:
            return None

        return render_to_string(template, context, request)


class ExportReportJSONView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher']

    def get(self, request, report_type, item_id, *args, **kwargs):
        school = self.get_school()
        report = ReportGenerator(school=school)

        data = {}

        if report_type == 'student':
            data = report.student_performance_report(item_id)
        elif report_type == 'class':
            data = report.class_performance_report()
        elif report_type == 'term':
            data = report.term_report()
        elif report_type == 'subject':
            data = report.subject_performance_report(item_id)
        elif report_type == 'marksheet':
            data = report.generate_marksheet(item_id, request.GET.get('term'))
        else:
            return HttpResponse("Invalid report type", status=400)

        if not data:
            return HttpResponse("No data found", status=404)

        return JsonResponse(data, safe=False)


class PrintMarksheetView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    template_name = "core/reports/print_marksheet.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher', 'student', 'parent']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        student_id = self.kwargs.get('student_id')
        term = self.request.GET.get('term')

        if not student_id and self.request.user.role == 'student':
            try:
                student = StudentProfile.objects.get(user=self.request.user)
                student_id = student.pk
            except StudentProfile.DoesNotExist:
                pass

        report = ReportGenerator(school=school)
        marksheet = report.generate_marksheet(student_id, term)

        if not marksheet:
            ctx['error'] = "No marks found for this student."
        else:
            ctx['marksheet'] = marksheet
            ctx['student'] = get_object_or_404(StudentProfile, pk=student_id)
            ctx['term'] = term

        return ctx


# ============================================================
# Report Card Views
# ============================================================

REPORT_CARD_ROLES = ['headteacher', 'dos']


class ReportCardListView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """List all generated report cards for the school, filterable by term/class."""
    template_name = "core/report_cards/list.html"
    required_roles = REPORT_CARD_ROLES

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        term = self.request.GET.get('term')
        class_id = self.request.GET.get('class_level')

        cards = ReportCard.objects.filter(school=school).select_related(
            'student__user', 'class_level', 'stream'
        )
        if term:
            cards = cards.filter(term=term)
        if class_id:
            cards = cards.filter(class_level_id=class_id)

        ctx['report_cards'] = cards
        ctx['classes'] = ClassLevel.objects.filter(school=school)
        ctx['terms'] = [t[0] for t in TERM_CHOICES]
        ctx['selected_term'] = term
        ctx['selected_class'] = class_id
        return ctx


class GenerateReportCardsView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    """
    Generate (or regenerate) report cards for all students in a class/term.
    Pulls existing Mid Term + End of Term marks, computes positions, saves cards.
    """
    required_roles = REPORT_CARD_ROLES

    def get(self, request):
        school = self.get_school()
        ctx = {
            'classes': ClassLevel.objects.filter(school=school),
            'terms': [t[0] for t in TERM_CHOICES],
        }
        return render(request, 'core/report_cards/generate.html', ctx)

    def post(self, request):
        school = self.get_school()
        term = request.POST.get('term')
        class_id = request.POST.get('class_level')

        if not term or not class_id:
            messages.error(request, "Please select both a term and a class.")
            return redirect('core:generate_report_cards')

        class_level = get_object_or_404(ClassLevel, pk=class_id, school=school)
        students = StudentProfile.objects.filter(
            school=school, class_level=class_level
        ).select_related('user', 'stream')

        if not students.exists():
            messages.warning(request, "No students found in this class.")
            return redirect('core:generate_report_cards')

        # Collect all subjects that have marks for this class/term
        subjects = Subject.objects.filter(
            school=school,
            mark__student__in=students,
            mark__term=term,
        ).distinct()

        # Build per-student aggregate scores for ranking
        student_totals = []
        for student in students:
            total = 0
            count = 0
            for subject in subjects:
                mid = float(Mark.objects.filter(
                    school=school, student=student, subject=subject,
                    term=term, exam='Mid Term'
                ).values_list('mid_term', flat=True).first() or 0)
                end = float(Mark.objects.filter(
                    school=school, student=student, subject=subject,
                    term=term, exam='End of Term'
                ).values_list('end_term', flat=True).first() or 0)
                total += mid + end
                count += 1
            avg = round(total / count, 2) if count else 0
            student_totals.append((student, avg))

        # Sort by average descending to assign positions
        student_totals.sort(key=lambda x: x[1], reverse=True)
        total_students = len(student_totals)

        cards_created = 0
        cards_updated = 0

        for position, (student, avg) in enumerate(student_totals, start=1):
            card, created = ReportCard.objects.get_or_create(
                school=school,
                student=student,
                term=term,
                defaults={
                    'class_level': class_level,
                    'stream': student.stream,
                    'generated_by': request.user,
                }
            )
            card.class_position  = position
            card.total_students  = total_students
            card.aggregate_score = avg
            card.class_level     = class_level
            card.stream          = student.stream
            card.generated_by    = request.user
            card.save()

            # Rebuild entries
            card.entries.all().delete()
            for subject in subjects:
                mid = float(Mark.objects.filter(
                    school=school, student=student, subject=subject,
                    term=term, exam='Mid Term'
                ).values_list('mid_term', flat=True).first() or 0)
                end = float(Mark.objects.filter(
                    school=school, student=student, subject=subject,
                    term=term, exam='End of Term'
                ).values_list('end_term', flat=True).first() or 0)
                ReportCardEntry.objects.create(
                    report_card=card,
                    subject=subject,
                    mid_term=mid,
                    end_term=end,
                )

            if created:
                cards_created += 1
            else:
                cards_updated += 1

        messages.success(
            request,
            f"Report cards generated: {cards_created} new, {cards_updated} updated "
            f"for {class_level} — {term}."
        )
        return redirect('core:report_card_list')


class ReportCardDetailView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """View a single student's report card."""
    template_name = "core/report_cards/detail.html"
    required_roles = REPORT_CARD_ROLES

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        card_id = self.kwargs.get('card_id')
        card = get_object_or_404(
            ReportCard.objects.prefetch_related('entries__subject'),
            pk=card_id, school=school
        )
        ctx['card'] = card
        ctx['entries'] = card.entries.select_related('subject').all()
        return ctx


class ReportCardEditView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, View):
    """Edit teacher comment and headteacher remark on a report card."""
    template_name = "core/report_cards/edit.html"
    required_roles = REPORT_CARD_ROLES

    def get(self, request, card_id):
        school = self.get_school()
        card = get_object_or_404(ReportCard, pk=card_id, school=school)
        return render(request, self.template_name, {'card': card})

    def post(self, request, card_id):
        school = self.get_school()
        card = get_object_or_404(ReportCard, pk=card_id, school=school)
        card.teacher_comment    = request.POST.get('teacher_comment', '').strip()
        card.headteacher_remark = request.POST.get('headteacher_remark', '').strip()
        card.save()
        messages.success(request, "Report card comments saved.")
        return redirect('core:report_card_detail', card_id=card.pk)


class ReportCardPrintView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """Print-friendly single report card."""
    template_name = "core/report_cards/print.html"
    required_roles = REPORT_CARD_ROLES

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        card_id = self.kwargs.get('card_id')
        card = get_object_or_404(
            ReportCard.objects.prefetch_related('entries__subject'),
            pk=card_id, school=school
        )
        ctx['card'] = card
        ctx['entries'] = card.entries.select_related('subject').all()
        ctx['school'] = school
        return ctx
