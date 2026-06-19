from django.http import HttpResponse
from core.models import StudentProfile
from core.services.report_service import build_student_report
from core.pdf.engine import render_pdf


def student_report_pdf(request, student_id):
    student = StudentProfile.objects.get(id=student_id)

    report = build_student_report(student)

    pdf = render_pdf("report_card.html", {
        "student": student,
        "school": student.class_level.school,
        "report": report["rows"],
        "total_points": report["total_points"],
        "term": "Term 1",
    }, request)

    return HttpResponse(pdf, content_type="application/pdf")