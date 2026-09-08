from django.db.models import Avg, Count, Sum, F, Q, ExpressionWrapper, FloatField, Max, Min
from django.db.models.functions import Coalesce
from .models import Mark, StudentProfile, ClassLevel, Subject, School
from .helpers import mark_average, grade_letter, grade_points
from collections import defaultdict
import json


class ReportGenerator:
    """Generate various academic reports"""
    
    def __init__(self, school=None, term=None, exam=None, class_level=None, stream=None):
        self.school = school
        self.term = term
        self.exam = exam
        self.class_level = class_level
        self.stream = stream
        self._marks_cache = None
    
    def get_marks_queryset(self):
        """Get filtered marks queryset"""
        qs = Mark.objects.select_related('student', 'subject', 'teacher')
        
        if self.school:
            qs = qs.filter(school=self.school)
        if self.term:
            qs = qs.filter(term=self.term)
        if self.exam:
            qs = qs.filter(exam=self.exam)
        if self.class_level:
            qs = qs.filter(student__class_level=self.class_level)
        if self.stream:
            qs = qs.filter(student__stream=self.stream)
        
        return qs
    
    def student_performance_report(self, student_id):
        """Generate individual student performance report"""
        marks = Mark.objects.filter(student_id=student_id).select_related('subject')
        
        if not marks.exists():
            return None
        
        # Group by term
        terms = {}
        for mark in marks:
            term_key = f"{mark.term} - {mark.exam}"
            if term_key not in terms:
                terms[term_key] = []
            terms[term_key].append(mark)
        
        # Calculate overall stats
        total_marks = marks.count()
        avg_score = mark_average(marks)
        total_points = sum(m.grade_points for m in marks)
        
        # Subject performance
        subject_performance = []
        subjects = marks.values_list('subject', flat=True).distinct()
        for subject_id in subjects:
            subject_marks = marks.filter(subject_id=subject_id)
            subject_avg = mark_average(subject_marks)
            subject_performance.append({
                'subject': subject_marks.first().subject.name,
                'average': subject_avg,
                'marks': len(subject_marks),
                'grades': [m.grade for m in subject_marks],
                'points': sum(m.grade_points for m in subject_marks),
            })
        
        return {
            'student_id': student_id,
            'total_marks': total_marks,
            'average_score': avg_score,
            'total_points': total_points,
            'terms': terms,
            'subject_performance': subject_performance,
            'grade_distribution': self._grade_distribution(marks),
        }
    
    def class_performance_report(self):
        """Generate class-wide performance report"""
        marks = self.get_marks_queryset()
        
        if not marks.exists():
            return None
        
        # Overall class stats
        total_students = StudentProfile.objects.filter(
            class_level=self.class_level
        ).count() if self.class_level else marks.values('student').distinct().count()
        
        avg_score = mark_average(marks)
        
        # Performance by subject
        subject_stats = []
        subjects = marks.values_list('subject', flat=True).distinct()
        for subject_id in subjects:
            subject_marks = marks.filter(subject_id=subject_id)
            subject_avg = mark_average(subject_marks)
            subject_stats.append({
                'subject': subject_marks.first().subject.name,
                'average': subject_avg,
                'student_count': subject_marks.values('student').distinct().count(),
                'highest': subject_marks.aggregate(highest=Max(Coalesce(F('mid_term') + F('end_term'), 0, output_field=FloatField()))).get('highest', 0),
                'lowest': subject_marks.aggregate(lowest=Min(Coalesce(F('mid_term') + F('end_term'), 0, output_field=FloatField()))).get('lowest', 0),
            })
        
        # Grade distribution
        grade_dist = self._grade_distribution(marks)
        
        return {
            'class_name': self.class_level.name if self.class_level else 'All Classes',
            'stream_name': self.stream.name if self.stream else 'All Streams',
            'total_students': total_students,
            'average_score': avg_score,
            'subject_stats': subject_stats,
            'grade_distribution': grade_dist,
            'pass_rate': self._pass_rate(marks),
        }
    
    def term_report(self):
        """Generate term-based performance report"""
        marks = self.get_marks_queryset()
        
        if not marks.exists():
            return None
        
        # Performance by class
        class_stats = []
        classes = marks.values_list('student__class_level', flat=True).distinct()
        for class_id in classes:
            class_marks = marks.filter(student__class_level_id=class_id)
            class_avg = mark_average(class_marks)
            class_stats.append({
                'class_name': class_marks.first().student.class_level.name,
                'students': class_marks.values('student').distinct().count(),
                'average': class_avg,
                'pass_rate': self._pass_rate(class_marks),
            })
        
        # Top performers
        top_performers = self._top_performers(marks, limit=10)
        
        return {
            'term': self.term,
            'exam': self.exam,
            'total_students': marks.values('student').distinct().count(),
            'overall_average': mark_average(marks),
            'class_stats': class_stats,
            'top_performers': top_performers,
            'grade_distribution': self._grade_distribution(marks),
            'pass_rate': self._pass_rate(marks),
        }
    
    def subject_performance_report(self, subject_id):
        """Generate subject-specific performance report"""
        marks = self.get_marks_queryset().filter(subject_id=subject_id)
        
        if not marks.exists():
            return None
        
        subject = marks.first().subject
        
        # Performance by class
        class_stats = []
        classes = marks.values_list('student__class_level', flat=True).distinct()
        for class_id in classes:
            class_marks = marks.filter(student__class_level_id=class_id)
            class_avg = mark_average(class_marks)
            class_stats.append({
                'class_name': class_marks.first().student.class_level.name,
                'students': class_marks.values('student').distinct().count(),
                'average': class_avg,
            })
        
        return {
            'subject_name': subject.name,
            'subject_code': subject.code,
            'total_students': marks.values('student').distinct().count(),
            'overall_average': mark_average(marks),
            'highest': marks.aggregate(highest=Max(F('mid_term') + F('end_term'))).get('highest', 0),
            'lowest': marks.aggregate(lowest=Min(F('mid_term') + F('end_term'))).get('lowest', 0),
            'class_stats': class_stats,
            'grade_distribution': self._grade_distribution(marks),
        }
    
    def _grade_distribution(self, marks):
        """Calculate grade distribution"""
        grades = [m.grade for m in marks]
        distribution = {}
        for grade in ['A', 'B', 'C', 'D', 'E', 'F']:
            count = grades.count(grade)
            if count > 0:
                distribution[grade] = {
                    'count': count,
                    'percentage': (count / len(grades)) * 100 if grades else 0
                }
        return distribution
    
    def _pass_rate(self, marks):
        """Calculate pass rate (C grade or higher)"""
        if not marks:
            return 0
        passing_grades = ['A', 'B', 'C']
        passing = sum(1 for m in marks if m.grade in passing_grades)
        return (passing / len(marks)) * 100
    
    def _top_performers(self, marks, limit=10):
        """Get top performing students"""
        student_avg = {}
        for student_id in marks.values_list('student', flat=True).distinct():
            student_marks = marks.filter(student_id=student_id)
            avg = mark_average(student_marks)
            if avg > 0:
                student = student_marks.first().student
                student_avg[student_id] = {
                    'student': student,
                    'average': avg,
                    'points': sum(m.grade_points for m in student_marks),
                }
        
        # Sort by average descending
        sorted_students = sorted(student_avg.items(), key=lambda x: x[1]['average'], reverse=True)
        return sorted_students[:limit]
    
    def generate_marksheet(self, student_id, term=None):
        """Generate a printable marksheet for a student"""
        marks = Mark.objects.filter(student_id=student_id)
        if term:
            marks = marks.filter(term=term)
        marks = marks.select_related('subject')
        
        if not marks.exists():
            return None
        
        student = marks.first().student
        
        # Group by term
        terms = {}
        for mark in marks:
            term_key = mark.term
            if term_key not in terms:
                terms[term_key] = []
            terms[term_key].append(mark)
        
        # Calculate overall performance
        total_marks = marks.count()
        avg_score = mark_average(marks)
        total_points = sum(m.grade_points for m in marks)
        
        return {
            'student': student,
            'student_name': student.user.get_full_name() or student.user.username,
            'admission_number': student.admission_number,
            'class': student.class_level.name if student.class_level else 'N/A',
            'stream': student.stream.name if student.stream else 'N/A',
            'school': student.school.name if student.school else 'N/A',
            'terms': terms,
            'total_marks': total_marks,
            'average_score': avg_score,
            'total_points': total_points,
            'grade': grade_letter(avg_score),
            'overall_performance': 'Excellent' if avg_score >= 80 else 'Good' if avg_score >= 65 else 'Average' if avg_score >= 50 else 'Needs Improvement',
        }