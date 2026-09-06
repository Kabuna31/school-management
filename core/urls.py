from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication & Home
    path('', views.RoleRedirectView.as_view(), name='role_redirect'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='core:login'), name='logout'),
    
    # Dashboards
    path('dashboard/superuser/', views.SuperuserDashboardView.as_view(), name='superuser_dashboard'),
    path('dashboard/school-admin/', views.SchooladminDashboardView.as_view(), name='schooladmin_dashboard'),
    path('dashboard/headteacher/', views.HeadteacherDashboardView.as_view(), name='headteacher_dashboard'),
    path('dashboard/dos/', views.DOSDashboardView.as_view(), name='dos_dashboard'),
    path('dashboard/teacher/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/parent/', views.ParentDashboardView.as_view(), name='parent_dashboard'),
    path('dashboard/bursar/', views.BursarDashboardView.as_view(), name='bursar_dashboard'),
    
    # Mark Management
    path('marks/entry/', views.TeacherMarkEntryView.as_view(), name='teacher_mark_entry'),
    path('marks/', views.SchoolMarksView.as_view(), name='school_marks'),
    path('marks/edit/<int:mark_id>/', views.SchoolMarkEditView.as_view(), name='school_mark_edit'),
    path('marks/delete/', views.DeleteMarkView.as_view(), name='delete_mark'),
    
    # Student & Class Views
    path('student/<int:student_id>/', views.StudentProfileView.as_view(), name='student_profile'),
    path('class/<int:class_id>/marks/', views.ClassMarksView.as_view(), name='class_marks'),
    
    # Reports
    path('reports/student/<int:student_id>/', views.StudentReportView.as_view(), name='student_report'),
    path('reports/student/<int:student_id>/pdf/', views.DownloadReportPDFView.as_view(), {'report_type': 'student'}, name='student_report_pdf'),
    path('reports/student/<int:student_id>/json/', views.ExportReportJSONView.as_view(), {'report_type': 'student'}, name='student_report_json'),
    
    path('reports/class/<int:class_id>/', views.ClassReportView.as_view(), name='class_report'),
    path('reports/class/<int:class_id>/pdf/', views.DownloadReportPDFView.as_view(), {'report_type': 'class'}, name='class_report_pdf'),
    path('reports/class/<int:class_id>/json/', views.ExportReportJSONView.as_view(), {'report_type': 'class'}, name='class_report_json'),
    
    path('reports/term/<str:term>/', views.TermReportView.as_view(), name='term_report'),
    path('reports/term/<str:term>/pdf/', views.DownloadReportPDFView.as_view(), {'report_type': 'term'}, name='term_report_pdf'),
    path('reports/term/<str:term>/json/', views.ExportReportJSONView.as_view(), {'report_type': 'term'}, name='term_report_json'),
    
    path('reports/subject/<int:subject_id>/', views.SubjectReportView.as_view(), name='subject_report'),
    path('reports/subject/<int:subject_id>/pdf/', views.DownloadReportPDFView.as_view(), {'report_type': 'subject'}, name='subject_report_pdf'),
    path('reports/subject/<int:subject_id>/json/', views.ExportReportJSONView.as_view(), {'report_type': 'subject'}, name='subject_report_json'),
    
    # Marksheet Views
    path('marksheet/<int:student_id>/', views.MarksheetView.as_view(), name='marksheet'),
    path('marksheet/<int:student_id>/pdf/', views.DownloadReportPDFView.as_view(), {'report_type': 'marksheet'}, name='marksheet_pdf'),
    path('marksheet/<int:student_id>/json/', views.ExportReportJSONView.as_view(), {'report_type': 'marksheet'}, name='marksheet_json'),
    path('marksheet/<int:student_id>/print/', views.PrintMarksheetView.as_view(), name='marksheet_print'),
    
    # Report Cards
    path('report-cards/', views.ReportCardListView.as_view(), name='report_card_list'),
    path('report-cards/generate/', views.GenerateReportCardsView.as_view(), name='generate_report_cards'),
    path('report-cards/<int:card_id>/', views.ReportCardDetailView.as_view(), name='report_card_detail'),
    path('report-cards/<int:card_id>/edit/', views.ReportCardEditView.as_view(), name='report_card_edit'),
    path('report-cards/<int:card_id>/print/', views.ReportCardPrintView.as_view(), name='report_card_print'),
    path('report-cards/<int:card_id>/delete/', views.ReportCardDeleteView.as_view(), name='report_card_delete'),  # ADD THIS LINE
    
    # Performance Analytics
    path('analytics/', views.PerformanceAnalyticsView.as_view(), name='analytics'),
    
    # Fix URLs (One-time fixes)
    path('create-admin/', views.CreateAdminView.as_view(), name='create_admin'),
    path('set-passwords/', views.set_username_as_password_view, name='set_passwords'),
    path('fix-admin/', views.fix_admin_permissions_view, name='fix_admin'),
    path('fix-school/', views.fix_school_view, name='fix_school'),
]