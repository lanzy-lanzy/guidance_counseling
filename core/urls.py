from django.urls import path
from core import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('schedule-session/', views.schedule_session, name='schedule_session'),
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
    path('appointments/<int:appointment_id>/start-session/', views.start_guidance_session, name='start_guidance_session'),
    path('appointments/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('guidance-sessions/<int:session_id>/', views.guidance_session_detail, name='guidance_session_detail'),
    path('guidance-sessions/<int:session_id>/start-followup/', views.start_followup_session, name='start_followup_session'),
    path('completed-sessions/', views.completed_sessions, name='completed_sessions'),
    path('sessions/history/', views.session_history, name='session_history'),
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/edit/', views.EditStudentView.as_view(), name='edit_student'),
    path('reports/', views.ReportsDashboardView.as_view(), name='reports_dashboard'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('reports/<int:report_id>/', views.view_report, name='view_report'),
    path('reports/export/excel/', views.export_report_excel, name='export_report_excel'),
    path('reports/export/pdf/', views.export_report_pdf, name='export_report_pdf'),
    path('students/<int:student_id>/interview/', views.create_interview_form, name='create_interview_form'),
    path('interview-forms/<int:form_id>/', views.view_interview_form, name='view_interview_form'),
]
