#--------------A grading helper.--------------------
def grade_point(score):

    if score >= 80:
        return ("A", 6)

    elif score >= 75:
        return ("B", 5)

    elif score >= 65:
        return ("C", 4)

    elif score >= 50:
        return ("D", 3)

    elif score >= 40:
        return ("E", 2)

    else:
        return ("F", 1)


marks = Mark.objects.filter(
    student=student,
    term=term
)

total_marks = 0
total_points = 0

for m in marks:

    total_marks += m.score

    grade, points = grade_point(
        m.score
    )

    total_points += points

average = (
    total_marks /
    marks.count()
    if marks.exists()
    else 0
)