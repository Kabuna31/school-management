from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, Count
from core.models import School, StudentProfile, EmployeeProfile, Subject, Mark


class HeadteacherDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "core/dashboards/headteacher.html"

    def test_func(self):
        return self.request.user.role == "headteacher"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.user.school
        marks = Mark.objects.filter(school=school)

        context.update({
            "school": school,
            "student_count": StudentProfile.objects.filter(school=school).count(),
            "staff_count": EmployeeProfile.objects.filter(school=school).count(),
            "class_count": school.classlevel_set.count(),
            "avg_score": marks.aggregate(a=Avg("score"))["a"],
            "top_students": marks.values(
                "student__user__first_name"
            ).annotate(avg=Avg("score")).order_by("-avg")[:5],
        })

        return context