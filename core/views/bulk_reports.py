import zipfile
from io import BytesIO
from django.http import HttpResponse
from core.models import StudentProfile
from core.services.report_service import build_student_report
from core.pdf.engine import render_pdf


def class_reports_zip(request, class_id):
    students = StudentProfile.objects.filter(class_level_id=class_id)

    buffer = BytesIO()
    zipf = zipfile.ZipFile(buffer, "w")

    for s in students:
        report = build_student_report(s)

        pdf = render_pdf("report_card.html", {
            "student": s,
            "school": s.class_level.school,
            "report": report["rows"],
            "term": "Term 1",
        })

        zipf.writestr(f"{s.user.first_name}_{s.id}.pdf", pdf)

    zipf.close()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="class_reports.zip"'
    return response