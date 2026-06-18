from django.shortcuts import render
from django.shortcuts import get_object_or_404

from core.models import (
    StudentProfile,
    ClassLevel
)

from core.reports.utils import (
    calculate_student_result,
    student_position
)


def report_card(
    request,
    student_id,
    term
):

    student = get_object_or_404(
        StudentProfile,
        pk=student_id
    )

    report = calculate_student_result(
        student,
        term
    )

    position = student_position(
        student,
        term
    )

    context = {
        "student": student,
        "report": report,
        "position": position,
        "term": term,
    }

    return render(
        request,
        "reports/report_card.html",
        context
    )


def class_analysis(
    request,
    class_id,
    term
):

    cls = get_object_or_404(
        ClassLevel,
        pk=class_id
    )

    students = cls.studentprofile_set.all()

    rows = []

    for s in students:

        report = calculate_student_result(
            s,
            term
        )

        rows.append(
            {
                "student": s,
                "avg": report["average"]
            }
        )

    rows.sort(
        key=lambda x: x["avg"],
        reverse=True
    )

    return render(
        request,
        "reports/class_analysis.html",
        {
            "classroom": cls,
            "rows": rows,
            "term": term
        }
    )