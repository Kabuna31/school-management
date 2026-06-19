from django.contrib import admin
from core.views import student_report_pdf
from core.views import class_reports_zip
from django.urls import path, include
from django.http import HttpResponse
import traceback

def health(request):
    return HttpResponse("ok", status=200)

def debug_view(request):
    try:
        from django.contrib.admin.sites import site
        from core.models import User
        ma = site._registry[User]
        form_class = ma.get_form(request, obj=None)
        return HttpResponse(f"OK: {form_class}")
    except Exception as e:
        return HttpResponse(
            f"<pre>{traceback.format_exc()}</pre>",
            status=200
        )

urlpatterns = [
    path('health/', health, name='health'),
    path('debug-user-form/', debug_view),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls', namespace='core')),
    path("reports/student/<int:student_id>/",student_report_pdf,name="student_report"),
    path("reports/class/<int:class_id>/",class_reports_zip,name="class_reports"),


]


