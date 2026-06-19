from core.models import Mark
from core.utils.grading import get_grade


def build_student_report(student):
    marks = Mark.objects.filter(student=student).select_related("subject")

    rows = []
    total_points = 0

    for m in marks:
        grade, points = get_grade(m.score)

        rows.append({
            "subject": m.subject.name,
            "fs": m.score,
            "grade": grade,
            "points": points
        })

        total_points += points

    return {
        "rows": rows,
        "total_points": total_points
    }