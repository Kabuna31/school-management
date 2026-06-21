from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Avg,
    Count,
    F,
    FloatField,
    ExpressionWrapper,
    Sum,
    Q,
    Max,
    Min,
)
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.views import LoginView
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission

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
    TERM_CHOICES,
    EXAM_CHOICES,
    MARK_MANAGE_ROLES,
    MARK_ENTRY_ROLES,
)
from .helpers import total_expr, mark_average, grade_letter, grade_points
from .reports import ReportGenerator


# ============================================================
# Fix Views (One-Time Fixes)
# ============================================================

def fix_school_view(request):
    """One-time view to fix school assignment for all users"""
    html = "<h1>Fixing School Assignment</h1>"
    
    # Create school if none exists
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
    
    # Assign all users to school
    count = 0
    for user in User.objects.filter(school__isnull=True):
        user.school = school
        user.save()
        count += 1
        html += f"<p>✅ Assigned {user.username} to {school.name}</p>"
    
    html += f"<p><strong>Total: {count} users assigned</strong></p>"
    html += '<p><a href="/admin/">Go to Admin Panel</a></p>'
    html += '<p><a href="/admin/core/classlevel/add/">Try Adding Class Level</a></p>'
    
    return HttpResponse(html)


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
    admin_user.user_permissions.set(Permission.objects.all())
    admin_user.save()
    
    html = f"""
    <h1>✅ Admin Permissions Fixed!</h1>
    <ul>
        <li>Username: {admin_user.username}</li>
        <li>Superuser: {admin_user.is_superuser}</li>
        <li>Staff: {admin_user.is_staff}</li>
        <li>Permissions: {admin_user.user_permissions.count()}</li>
    </ul>
    <p><a href="/admin/">Go to Admin Panel</a></p>
    """
    return HttpResponse(html)


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


class CreateAdminView(View):
    """One-time view to create admin user"""
    
    def get(self, request):
        User = get_user_model()
        
        # Check if admin exists
        if User.objects.filter(username='admin').exists():
            return HttpResponse("""
                <h1>✅ Admin already exists!</h1>
                <p>Username: admin</p>
                <p>Password: admin123456</p>
                <p><a href="/login/">Go to Login</a></p>
            """)
        
        # Create admin
        User.objects.create_superuser(
            username='admin',
            email='admin@school.com',
            password='admin123456'
        )
        
        return HttpResponse("""
            <h1>✅ Admin created successfully!</h1>
            <p>Username: <strong>admin</strong></p>
            <p>Password: <strong>admin123456</strong></p>
            <p><a href="/login/">Go to Login</a></p>
        """)


# ============================================================
# Custom Login View
# ============================================================

class CustomLoginView(LoginView):
    """Custom login view that redirects based on role"""
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        user = self.request.user
        role_map = {
            "system_admin": "core:superuser_dashboard",
            "school_admin": "core:schooladmin_dashboard",
            "headteacher": "core:headteacher_dashboard",
            "dos": "core:dos_dashboard",
            "teacher": "core:teacher_dashboard",
            "class_teacher": "core:teacher_dashboard",
            "student": "core:student_dashboard",
            "parent": "core:parent_dashboard",
            "bursar": "core:bursar_dashboard",
        }
        return reverse(role_map.get(user.role, "admin:index"))


# ============================================================
# Permission Mixins
# ============================================================

class RoleRequiredMixin:
    """Mixin to require specific user roles"""
    required_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('core:login'))
        
        if not self.required_roles:
            return super().dispatch(request, *args, **kwargs)
        
        # Superusers and system admins can access everything
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
        """Get the school for the current user"""
        if hasattr(self.request.user, 'school'):
            return self.request.user.school
        return None
    
    def dispatch(self, request, *args, **kwargs):
        # Superusers can access everything
        if request.user.role == 'system_admin' or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")
        return super().dispatch(request, *args, **kwargs)


# ============================================================
# Role Redirect View
# ============================================================

class RoleRedirectView(View):
    """Redirect users to their appropriate dashboard based on role"""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('core:login')
        
        role_map = {
            "system_admin": "core:superuser_dashboard",
            "school_admin": "core:schooladmin_dashboard",
            "headteacher": "core:headteacher_dashboard",
            "dos": "core:dos_dashboard",
            "teacher": "core:teacher_dashboard",
            "class_teacher": "core:teacher_dashboard",
            "student": "core:student_dashboard",
            "parent": "core:parent_dashboard",
            "bursar": "core:bursar_dashboard",
        }
        
        redirect_url = role_map.get(
            request.user.role,
            "admin:index"
        )
        
        return redirect(redirect_url)


# ============================================================
# Dashboard Views
# ============================================================

class SuperuserDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Dashboard for system administrators"""
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
    """Dashboard for school administrators"""
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
        ctx["recent_marks"] = marks.select_related(
            "student", "subject", "teacher"
        ).order_by("-id")[:10]
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        
        return ctx


class HeadteacherDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """Dashboard for headteachers"""
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
        ctx["recent_marks"] = marks.select_related(
            "student", "subject", "teacher"
        ).order_by("-id")[:10]
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        
        return ctx


class DOSDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """Dashboard for Director of Studies"""
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
        ctx["recent_marks"] = marks.select_related(
            "student", "subject", "teacher"
        ).order_by("-id")[:10]
        ctx["classes"] = ClassLevel.objects.filter(school=school)
        
        return ctx


class TeacherDashboardView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """Dashboard for teachers"""
    template_name = "core/dashboard/teacher.html"
    required_roles = ['teacher', 'class_teacher']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        school = self.get_school()
        if not school:
            return ctx
        
        try:
            teacher = EmployeeProfile.objects.get(user=self.request.user)
            marks = Mark.objects.filter(
                school=school,
                teacher=teacher
            )
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
    """Dashboard for bursars"""
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
    """Dashboard for students"""
    template_name = "core/dashboard/student.html"
    required_roles = ['student']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        try:
            student = StudentProfile.objects.select_related(
                "class_level", "stream"
            ).get(user=self.request.user)
            
            marks = Mark.objects.filter(
                student=student
            ).select_related("subject")
            
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
    """Dashboard for parents"""
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
    """View for entering marks"""
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
                class_level_id=selected_class,
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
            class_level_id=class_level,
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
                
                mark, created = Mark.objects.get_or_create(
                    school=school,
                    student=student,
                    subject_id=subject,
                    term=term,
                    exam=exam,
                    defaults={"teacher": teacher}
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
    """View for viewing all marks in a school"""
    template_name = "core/school_admin/marks.html"
    required_roles = MARK_MANAGE_ROLES
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        school = self.get_school()
        if not school:
            return ctx
        
        marks = Mark.objects.filter(
            school=school
        ).select_related("student", "subject", "teacher")
        
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
    """View for editing a single mark"""
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
    """View for deleting a mark"""
    required_roles = MARK_MANAGE_ROLES
    
    def post(self, request):
        school = self.get_school()
        if not school:
            return HttpResponseForbidden("You are not associated with a school.")
        
        mark_id = request.POST.get("mark_id")
        if not mark_id:
            return redirect("core:school_marks")
        
        mark = Mark.objects.filter(
            pk=mark_id,
            school=school
        ).first()
        
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
    """View for viewing a student's profile and marks"""
    template_name = "core/student_profile.html"
    required_roles = ['school_admin', 'headteacher', 'dos', 'teacher', 'class_teacher', 'student', 'parent']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        school = self.get_school()
        if not school:
            return ctx
        
        student_id = self.kwargs.get('student_id')
        student = get_object_or_404(StudentProfile, pk=student_id, school=school)
        
        # Check if user has permission to view this student
        user = self.request.user
        if user.role == 'student':
            try:
                viewer_student = StudentProfile.objects.get(user=user)
                if viewer_student.pk != student.pk:
                    return HttpResponseForbidden("You can only view your own profile.")
            except StudentProfile.DoesNotExist:
                return HttpResponseForbidden("Student profile not found.")
        
        if user.role == 'parent':
            try:
                parent = ParentProfile.objects.get(user=user)
                if student not in parent.children.all():
                    return HttpResponseForbidden("You can only view your children's profiles.")
            except ParentProfile.DoesNotExist:
                return HttpResponseForbidden("Parent profile not found.")
        
        marks = Mark.objects.filter(
            student=student
        ).select_related("subject", "teacher")
        
        marks_by_exam = {}
        for mark in marks:
            key = f"{mark.term} - {mark.exam}"
            if key not in marks_by_exam:
                marks_by_exam[key] = []
            marks_by_exam[key].append(mark)
        
        ctx["student"] = student
        ctx["marks"] = marks
        ctx["marks_by_exam"] = marks_by_exam
        ctx["avg_score"] = mark_average(marks)
        ctx["total_points"] = sum([m.grade_points for m in marks])
        
        return ctx


class ClassMarksView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """View for viewing marks for an entire class"""
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
            school=school,
            class_level=class_level
        ).select_related("user", "stream")
        
        student_ids = students.values_list('pk', flat=True)
        marks = Mark.objects.filter(
            student__in=student_ids
        ).select_related("student", "subject", "teacher")
        
        marks_by_student = {}
        for student in students:
            marks_by_student[student.pk] = []
        
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
    """View student performance report"""
    template_name = "core/reports/student_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher', 'student', 'parent']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        student_id = self.kwargs.get('student_id')
        school = self.get_school()
        
        # If it's a student viewing their own report
        if not student_id and self.request.user.role == 'student':
            try:
                student = StudentProfile.objects.get(user=self.request.user)
                student_id = student.pk
            except StudentProfile.DoesNotExist:
                pass
        
        # If it's a parent viewing their child's report
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
    """View class performance report"""
    template_name = "core/reports/class_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        school = self.get_school()
        class_id = self.kwargs.get('class_id')
        term = self.request.GET.get('term')
        exam = self.request.GET.get('exam')
        
        report = ReportGenerator(
            school=school,
            class_level_id=class_id if class_id else None,
            term=term,
            exam=exam
        )
        
        ctx['report'] = report.class_performance_report()
        ctx['class_level'] = get_object_or_404(ClassLevel, pk=class_id, school=school) if class_id else None
        ctx['terms'] = [t[0] for t in TERM_CHOICES]
        ctx['exams'] = [e[0] for e in EXAM_CHOICES]
        ctx['selected_term'] = term
        ctx['selected_exam'] = exam
        
        return ctx


class TermReportView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """View term performance report"""
    template_name = "core/reports/term_report.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        school = self.get_school()
        term = self.kwargs.get('term')
        exam = self.request.GET.get('exam')
        
        report = ReportGenerator(
            school=school,
            term=term,
            exam=exam
        )
        
        ctx['report'] = report.term_report()
        ctx['term'] = term
        ctx['exam'] = exam
        ctx['exams'] = [e[0] for e in EXAM_CHOICES]
        
        return ctx


class SubjectReportView(LoginRequiredMixin, RoleRequiredMixin, SchoolScopedMixin, TemplateView):
    """View subject performance report"""
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
    """View printable marksheet"""
    template_name = "core/reports/marksheet.html"
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher', 'student', 'parent']
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        school = self.get_school()
        student_id = self.kwargs.get('student_id')
        term = self.request.GET.get('term')
        
        # If student viewing their own marksheet
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
# Download/Export Views
# ============================================================

class DownloadReportPDFView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Download report as PDF"""
    required_roles = ['system_admin', 'school_admin', 'headteacher', 'dos', 'teacher']
    
    def get(self, request, report_type, item_id, *args, **kwargs):
        school = request.user.school if request.user.role != 'system_admin' else None
        
        # Generate HTML from template
        html_string = self._get_report_html(request, report_type, item_id, school)
        
        if not html_string:
            return HttpResponse("Report not found", status=404)
        
        # Try to generate PDF
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
            # If weasyprint not installed, return HTML version
            response = HttpResponse(html_string, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{item_id}.html"'
            return response
    
    def _get_report_html(self, request, report_type, item_id, school):
        """Get HTML for the report"""
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
           