from django.urls import path

from .views_reports import (
    report_card,
    class_analysis
)

urlpatterns = [

    path(
        "report-card/<int:student_id>/<str:term>/",
        report_card,
        name="report_card"
    ),

    path(
        "class-analysis/<int:class_id>/<str:term>/",
        class_analysis,
        name="class_analysis"
    ),

]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)