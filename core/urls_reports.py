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