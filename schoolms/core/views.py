from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.db.models import Avg, Count, Max
from .models import (
    School, ClassLevel, Stream, Subject,
    StudentProfile, EmployeeProfile, ParentProfile, Mark
)

ADMIN_ROLES  = ['system_admin', 'headteacher']
STAFF_ROLES  = ['teacher', 'class_teacher', 'dos']
ALLOWED_MARK_ENTRY_ROLES = ADMIN_ROLES + STAFF_ROLES


# ── Role Router ────────────────────────────────────────────────────────────

class RoleRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        role_map = {
            'system_admin':   reverse('core:superuser_dashboard'),
            'headteacher':    reverse('core:headteacher_dashboard'),
            'dos':            reverse('core:dos_dashboard'),
            'bursar':         reverse('core:bursar_dashboard'),
            'teacher':        reverse('core:teacher_dashboard'),
            'class_teacher':  reverse('core:teacher_dashboard'),
            'student':        reverse('core:student_dashboard'),
            'parent':         reverse('core:parent_dashboard'),
        }
        return role_map.get(self.request.user.role, '/admin/')

    @staticmethod
    def _safe_reverse(url_name, fallback='/'):
        try:
            return reverse(url_name)
        except Exception:
            return fallback


# ── Superuser / System Owner Dashboard ────────────────────────────────────

class SuperuserDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/superuser.html'

    def test_func(self):
        return self.request.user.role in ["system_admin"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'school_count':   School.objects.count(),
            'student_count':  StudentProfile.objects.count(),
            'staff_count':    EmployeeProfile.objects.count(),
            'subject_count':  Subject.objects.count(),
            'mark_count':     Mark.objects.count(),
            'avg_score':      Mark.objects.aggregate(a=Avg('score'))['a'],
            'schools':        School.objects.annotate(
                                students=Count('studentprofile'),
                                staff=Count('employeeprofile'),
                              ).order_by('name'),
            'recent_marks':   Mark.objects.select_related(
                                'student__user', 'subject', 'teacher__user'
                              ).order_by('-id')[:10],
        })
        return context


# ── Headteacher Dashboard ──────────────────────────────────────────────────

class HeadteacherDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/headteacher.html'

    def test_func(self):
        return self.request.user.role == 'headteacher'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.user.school
        context.update({
            'school':         school,
            'student_count':  StudentProfile.objects.filter(school=school).count(),
            'staff_count':    EmployeeProfile.objects.filter(school=school).count(),
            'class_count':    ClassLevel.objects.filter(school=school).count(),
            'subject_count':  Subject.objects.filter(school=school).count(),
            'mark_count':     Mark.objects.filter(school=school).count(),
            'avg_score':      Mark.objects.filter(school=school).aggregate(a=Avg('score'))['a'],
            'classes':        ClassLevel.objects.filter(school=school).annotate(
                                students=Count('studentprofile')
                              ).order_by('name'),
            'subject_avgs':   Subject.objects.filter(school=school).annotate(
                                avg=Avg('mark__score'),
                                total=Count('mark'),
                              ).order_by('name'),
            'recent_marks':   Mark.objects.filter(school=school).select_related(
                                'student__user', 'subject', 'teacher__user'
                              ).order_by('-id')[:10],
            'top_students':   Mark.objects.filter(school=school).values(
                                'student__user__first_name',
                                'student__user__last_name',
                                'student__admission_number',
                              ).annotate(avg=Avg('score')).order_by('-avg')[:5],
        })
        return context


# ── Director of Studies Dashboard ─────────────────────────────────────────

class DOSDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/dos.html'

    def test_func(self):
        return self.request.user.role == 'dos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.user.school
        context.update({
            'school':        school,
            'student_count': StudentProfile.objects.filter(school=school).count(),
            'class_count':   ClassLevel.objects.filter(school=school).count(),
            'mark_count':    Mark.objects.filter(school=school).count(),
            'avg_score':     Mark.objects.filter(school=school).aggregate(a=Avg('score'))['a'],
            'classes':       ClassLevel.objects.filter(school=school).annotate(
                               students=Count('studentprofile'),
                               avg_score=Avg('studentprofile__mark__score'),
                             ).order_by('name'),
            'subject_avgs':  Subject.objects.filter(school=school).annotate(
                               avg=Avg('mark__score'),
                               total=Count('mark'),
                             ).order_by('-avg'),
            'recent_marks':  Mark.objects.filter(school=school).select_related(
                               'student__user', 'subject', 'teacher__user'
                             ).order_by('-id')[:15],
            'terms':         ['Term 1', 'Term 2', 'Term 3'],
        })
        return context


# ── Bursar Dashboard ───────────────────────────────────────────────────────

class BursarDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/bursar.html'

    def test_func(self):
        return self.request.user.role == 'bursar'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.user.school
        context.update({
            'school':        school,
            'student_count': StudentProfile.objects.filter(school=school).count(),
            'staff_count':   EmployeeProfile.objects.filter(school=school).count(),
            'class_count':   ClassLevel.objects.filter(school=school).count(),
            'classes':       ClassLevel.objects.filter(school=school).annotate(
                               students=Count('studentprofile')
                             ).order_by('name'),
            'profile':       getattr(self.request.user, 'employeeprofile', None),
        })
        return context


# ── Teacher / Class Teacher Dashboard ─────────────────────────────────────

class TeacherDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/teacher.html'

    def test_func(self):
        return self.request.user.role in ['teacher', 'class_teacher']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school  = self.request.user.school
        profile = getattr(self.request.user, 'employeeprofile', None)
        context.update({
            'school':        school,
            'profile':       profile,
            'student_count': StudentProfile.objects.filter(school=school).count(),
            'mark_count':    Mark.objects.filter(school=school, teacher=profile).count() if profile else 0,
            'avg_score':     Mark.objects.filter(school=school, teacher=profile).aggregate(a=Avg('score'))['a'] if profile else None,
            'subjects':      Subject.objects.filter(school=school),
            'classes':       ClassLevel.objects.filter(school=school),
            'recent_marks':  Mark.objects.filter(school=school, teacher=profile).select_related(
                               'student__user', 'subject'
                             ).order_by('-id')[:10] if profile else [],
            'subject_avgs':  Mark.objects.filter(school=school, teacher=profile).values(
                               'subject__name'
                             ).annotate(avg=Avg('score'), total=Count('id')).order_by('subject__name') if profile else [],
        })
        return context


# ── Student Dashboard ──────────────────────────────────────────────────────

class StudentDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/student.html'

    def test_func(self):
        return self.request.user.role == 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'studentprofile', None)
        if profile:
            marks = Mark.objects.filter(student=profile).select_related('subject')
            context.update({
                'profile':     profile,
                'marks':       marks.order_by('term', 'subject__name'),
                'avg_score':   marks.aggregate(a=Avg('score'))['a'],
                'mark_count':  marks.count(),
                'best_subject': marks.values('subject__name').annotate(
                                  avg=Avg('score')
                                ).order_by('-avg').first(),
                'term_avgs':   marks.values('term').annotate(
                                  avg=Avg('score')
                                ).order_by('term'),
            })
        return context


# ── Parent Dashboard ───────────────────────────────────────────────────────

class ParentDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'core/dashboards/parent.html'

    def test_func(self):
        return self.request.user.role == 'parent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'parentprofile', None)
        if profile:
            children = profile.children.select_related(
                'user', 'class_level', 'stream'
            ).all()
            children_data = []
            for child in children:
                marks = Mark.objects.filter(student=child).select_related('subject')
                children_data.append({
                    'child':      child,
                    'marks':      marks.order_by('term', 'subject__name'),
                    'avg_score':  marks.aggregate(a=Avg('score'))['a'],
                    'mark_count': marks.count(),
                    'term_avgs':  marks.values('term').annotate(avg=Avg('score')).order_by('term'),
                })
            context.update({
                'profile':       profile,
                'children_data': children_data,
                'child_count':   children.count(),
            })
        return context


# ── Mark Entry (Teachers / DOS / Admin) ───────────────────────────────────

class TeacherMarkEntryView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.role in ALLOWED_MARK_ENTRY_ROLES

    def get(self, request, *args, **kwargs):
        school = getattr(request.user, 'school', None)
        if not school:
            return redirect('core:role_redirect')

        selected_class   = request.GET.get('class_level')
        selected_stream  = request.GET.get('stream')
        selected_subject = request.GET.get('subject')
        selected_term    = request.GET.get('term')

        context = {
            'classes':          ClassLevel.objects.filter(school=school),
            'streams':          Stream.objects.filter(school=school),
            'subjects':         Subject.objects.filter(school=school),
            'terms':            ['Term 1', 'Term 2', 'Term 3'],
            'selected_class':   selected_class,
            'selected_stream':  selected_stream,
            'selected_subject': selected_subject,
            'selected_term':    selected_term,
            'success':          request.GET.get('success'),
        }

        if selected_class and selected_stream:
            context['students'] = StudentProfile.objects.filter(
                school=school,
                class_level_id=selected_class,
                stream_id=selected_stream,
            ).order_by('user__first_name')

            if selected_subject and selected_term:
                marks = Mark.objects.filter(
                    school=school,
                    subject_id=selected_subject,
                    term=selected_term,
                    student__class_level_id=selected_class,
                    student__stream_id=selected_stream,
                )
                context['existing_marks'] = {m.student_id: m.score for m in marks}

        return render(request, 'core/teacher_mark_entry.html', context)

    def post(self, request, *args, **kwargs):
        school = getattr(request.user, 'school', None)
        if not school:
            return redirect('core:role_redirect')

        class_id   = request.POST.get('class_level')
        stream_id  = request.POST.get('stream')
        subject_id = request.POST.get('subject')
        term       = request.POST.get('term')
        teacher_profile = getattr(request.user, 'employeeprofile', None)

        if not all([class_id, stream_id, subject_id, term]):
            return redirect('core:role_redirect')

        errors = []
        for key, value in request.POST.items():
            if key.startswith('student_') and value.strip():
                try:
                    student_id = key.split('_')[-1]
                    score = float(value)
                    if not (0 <= score <= 100):
                        errors.append(f"Score {score} out of range.")
                        continue
                    Mark.objects.update_or_create(
                        school=school,
                        student_id=student_id,
                        subject_id=subject_id,
                        term=term,
                        defaults={'score': score, 'teacher': teacher_profile}
                    )
                except (ValueError, TypeError):
                    errors.append(f"Invalid score '{value}' skipped.")
                    continue

        url    = reverse('core:teacher_mark_entry')
        status = 'true' if not errors else 'partial'
        return redirect(
            f"{url}?class_level={class_id}&stream={stream_id}"
            f"&subject={subject_id}&term={term}&success={status}"
        )
