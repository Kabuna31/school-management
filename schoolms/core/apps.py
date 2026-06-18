from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Patch the default admin site index to inject dashboard stats."""
        from django.contrib import admin
        from django.db.models import Avg

        original_index = admin.site.__class__.index

        def patched_index(self, request, extra_context=None):
            from core.models import (
                School, StudentProfile, EmployeeProfile,
                Subject, Mark
            )
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
            return original_index(self, request, extra_context)

        admin.site.__class__.index = patched_index
