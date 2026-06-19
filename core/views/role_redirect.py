from django.views.generic import RedirectView
from django.urls import reverse


class RoleRedirectView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        role = getattr(self.request.user, "role", None)

        map_roles = {
            "system_admin": reverse("core:superuser_dashboard"),
            "school_admin": reverse("core:schooladmin_dashboard"),
            "headteacher": reverse("core:headteacher_dashboard"),
            "teacher": reverse("core:teacher_dashboard"),
            "student": reverse("core:student_dashboard"),
            "parent": reverse("core:parent_dashboard"),
        }

        return map_roles.get(role, "/admin/")