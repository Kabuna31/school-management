def get_grade(score):
    if score >= 80:
        return "A", 5
    elif score >= 70:
        return "B", 4
    elif score >= 60:
        return "C", 3
    elif score >= 50:
        return "D", 2
    return "E", 1