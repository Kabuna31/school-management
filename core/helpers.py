from django.db.models import Avg, F, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce


def total_expr():
    """Expression wrapper for calculating total score (mid_term + end_term)"""
    return ExpressionWrapper(
        Coalesce(F("mid_term"), 0) +
        Coalesce(F("end_term"), 0),
        output_field=FloatField()
    )


def mark_average(qs):
    """Calculate average total score from a queryset of marks"""
    if not qs or qs.count() == 0:
        return 0
    return qs.annotate(
        total=total_expr()
    ).aggregate(
        avg=Avg("total")
    )["avg"] or 0


def grade_letter(score):
    """Convert numeric score to letter grade"""
    if score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    return "F"


def grade_points(letter):
    """Convert letter grade to points"""
    return {
        "A": 5,
        "B": 4,
        "C": 3,
        "D": 2,
        "F": 1,
    }.get(letter, 0)
