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
