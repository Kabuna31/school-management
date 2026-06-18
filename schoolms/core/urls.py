from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.RoleRedirectView.as_view(), name='role_redirect'),

    # Dashboards
    path('dashboard/superuser/',   views.SuperuserDashboardView.as_view(),   name='superuser_dashboard'),
    path('dashboard/headteacher/', views.HeadteacherDashboardView.as_view(), name='headteacher_dashboard'),
    path('dashboard/dos/',         views.DOSDashboardView.as_view(),         name='dos_dashboard'),
    path('dashboard/bursar/',      views.BursarDashboardView.as_view(),      name='bursar_dashboard'),
    path('dashboard/teacher/',     views.TeacherDashboardView.as_view(),     name='teacher_dashboard'),
    path('dashboard/student/',     views.StudentDashboardView.as_view(),     name='student_dashboard'),
    path('dashboard/parent/',      views.ParentDashboardView.as_view(),      name='parent_dashboard'),

    # Mark entry
    path('marks/entry/', views.TeacherMarkEntryView.as_view(), name='teacher_mark_entry'),
]
