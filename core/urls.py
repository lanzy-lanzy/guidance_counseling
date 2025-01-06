from django.urls import path
from core import views
from . import admin_views, counselor_views, student_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),  # Keep this as a fallback
    path('schedule-session/', views.schedule_session, name='schedule_session'),
   
    # Student URLs
    path('student/dashboard/', student_views.student_dashboard, name='student_dashboard'),
    path('student/appointments/', student_views.student_appointment_list, name='student_appointment_list'),
    path('student/sessions/history/', student_views.student_session_history, name='student_session_history'),
    path('student/interviews/', student_views.student_interview_forms, name='student_interview_forms'),
    path('student/counselors/', student_views.student_counselor_list, name='student_counselor_list'),
    path('student/appointments/request/', student_views.request_appointment, name='request_appointment'),
    path('student/appointments/<int:appointment_id>/cancel/', student_views.cancel_appointment, name='cancel_appointment'),
    path('student/profile/', student_views.student_profile, name='student_profile'),

    # Counselor URLs
    # path('counselor/appointments/', counselor_views.appointments, name='counselor_appointments'),
    path('counselor/dashboard/', counselor_views.counselor_dashboard, name='counselor_dashboard'),
    path('counselor/appointments/', counselor_views.counselor_appointment_list, name='counselor_appointment_list'),
    path('counselor/students/', counselor_views.counselor_student_list, name='counselor_student_list'),
    path('counselor/sessions/history/', counselor_views.counselor_session_history, name='counselor_session_history'),
    path('counselor/reports/', counselor_views.counselor_reports_dashboard, name='counselor_reports_dashboard'),
    path('counselor/appointments/<int:appointment_id>/approve/', counselor_views.approve_appointment, name='approve_appointment'),
    path('counselor/appointments/<int:appointment_id>/decline/', counselor_views.decline_appointment, name='decline_appointment'),
    path('counselor/appointments/<int:appointment_id>/start-session/', counselor_views.start_session, name='start_session'),
    path('counselor/sessions/<int:session_id>/end/', counselor_views.end_session, name='end_session'),
    path('counselor/student/<int:student_id>/', counselor_views.student_profile, name='student_profile'),
    path('counselor/student/<int:student_id>/create-interview/', counselor_views.create_interview, name='create_interview'),
    path('counselor/profile/', counselor_views.counselor_profile, name='counselor_profile'),

    path('interview/<int:interview_id>/', counselor_views.interview_form, name='interview_form'),
    path('interview/<int:interview_id>/', views.view_interview, name='view_interview'),

    # Admin URLs
    path('admin-panel/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', admin_views.admin_users, name='admin_users'),
    path('admin-panel/users/add/', admin_views.admin_add_user, name='admin_add_user'),
    path('admin-panel/users/<int:user_id>/edit/', admin_views.admin_edit_user, name='admin_edit_user'),
    path('admin-panel/users/<int:user_id>/delete/', admin_views.admin_delete_user, name='admin_delete_user'),
    path('admin-panel/users/<int:user_id>/approve/', admin_views.admin_approve_user, name='admin_approve_user'),
    path('admin-panel/students/', admin_views.admin_students, name='admin_students'),
    path('admin-panel/counselors/', admin_views.admin_counselors, name='admin_counselors'),
    path('admin-panel/appointments/', admin_views.admin_appointments, name='admin_appointments'),
    path('admin-panel/reports/', admin_views.admin_reports, name='admin_reports'),
    path('admin-panel/settings/', admin_views.admin_settings, name='admin_settings'),
]
