from django.apps import AppConfig
from django.db.models import Avg, ExpressionWrapper, F, FloatField


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Patch admin index to show average score
        try:
            from django.contrib.admin.sites import AdminSite
            from .models import Mark
            
            original_index = AdminSite.index
            
            def patched_index(self, request, extra_context=None):
                extra_context = extra_context or {}
                
                # Calculate average using the correct fields
                avg = Mark.objects.annotate(
                    total=ExpressionWrapper(
                        F('mid_term') + F('end_term'), 
                        output_field=FloatField()
                    )
                ).aggregate(a=Avg('total'))['a']
                
                extra_context['avg_score'] = f"{avg:.1f}" if avg is not None else '—'
                return original_index(self, request, extra_context)
            
            AdminSite.index = patched_index
            
        except Exception:
            # If there's an error, just skip the patch
            pass