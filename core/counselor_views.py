from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView
from django.contrib import messages
from .models import Appointment, Student, GuidanceSession, Interview, Counselor
from django.utils import timezone

def is_counselor(user):
    return user.is_authenticated and user.role == 'counselor'

@login_required
@user_passes_test(is_counselor)
def counselor_dashboard(request):
    counselor = get_object_or_404(Counselor, user=request.user)
    pending_appointments = Appointment.objects.filter(counselor=counselor, status='pending').count()
    total_students = Student.objects.count()
    completed_sessions = GuidanceSession.objects.filter(counselor=counselor, status='completed').count()
    
    context = {
        'pending_appointments': pending_appointments,
        'total_students': total_students,
        'completed_sessions': completed_sessions,
        'upcoming_appointments': Appointment.objects.filter(
            counselor=counselor,
            date__gte=timezone.now().date()
        ).order_by('date', 'time')[:5],
        'recent_interviews': Interview.objects.filter(counselor=counselor).order_by('-date')[:5]
    }
    return render(request, 'counselor/dashboard.html', context)

@login_required
@user_passes_test(is_counselor)
def counselor_appointment_list(request):
    counselor = get_object_or_404(Counselor, user=request.user)
    appointments = Appointment.objects.filter(counselor=counselor).order_by('-date', '-time')
    return render(request, 'counselor/appointments.html', {'appointments': appointments})

@login_required
@user_passes_test(is_counselor)
def counselor_student_list(request):
    students = Student.objects.all().order_by('user__last_name', 'user__first_name')
    return render(request, 'counselor/students.html', {'students': students})

@login_required
@user_passes_test(is_counselor)
def counselor_session_history(request):
    counselor = get_object_or_404(Counselor, user=request.user)
    sessions = GuidanceSession.objects.filter(counselor=counselor).order_by('-date')
    return render(request, 'counselor/session_history.html', {'sessions': sessions})

@login_required
@user_passes_test(is_counselor)
def counselor_reports_dashboard(request):
    counselor = get_object_or_404(Counselor, user=request.user)
    context = {
        'total_sessions': GuidanceSession.objects.filter(counselor=counselor).count(),
        'total_students': Student.objects.count(),
        'recent_sessions': GuidanceSession.objects.filter(counselor=counselor).order_by('-date')[:5]
    }
    return render(request, 'counselor/reports.html', context)

@login_required
@user_passes_test(is_counselor)
def approve_appointment(request, appointment_id):
    counselor = get_object_or_404(Counselor, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, counselor=counselor)
    appointment.status = 'approved'
    appointment.save()
    messages.success(request, 'Appointment approved successfully.')
    return redirect('counselor_appointment_list')

@login_required
@user_passes_test(is_counselor)
def decline_appointment(request, appointment_id):
    counselor = get_object_or_404(Counselor, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, counselor=counselor)
    appointment.status = 'declined'
    appointment.save()
    messages.success(request, 'Appointment declined successfully.')
    return redirect('counselor_appointment_list')

@login_required
@user_passes_test(is_counselor)
def start_session(request, appointment_id):
    counselor = get_object_or_404(Counselor, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, counselor=counselor, status='approved')
    
    # Create a new guidance session
    session = GuidanceSession.objects.create(
        student=appointment.student,
        counselor=counselor,
        session_type='Interview',  # Default type, can be modified later
        status='scheduled',
        appointment=appointment
    )
    
    # Start the session using the model's method
    session.start_session()
    
    # Update appointment status
    appointment.status = 'completed'
    appointment.save()
    
    messages.success(request, 'Session started successfully.')
    return redirect('counselor_session_history')

@login_required
@user_passes_test(is_counselor)
def end_session(request, session_id):
    counselor = get_object_or_404(Counselor, user=request.user)
    session = get_object_or_404(GuidanceSession, id=session_id, counselor=counselor, status='in_progress')
    
    if request.method == 'POST':
        # End the session with the provided details
        session.end_session(
            problem_statement=request.POST.get('problem_statement'),
            recommendations=request.POST.get('recommendations'),
            notes=request.POST.get('notes'),
            action_items=request.POST.get('action_items'),
            next_steps=request.POST.get('next_steps')
        )
        messages.success(request, 'Session ended successfully.')
        return redirect('counselor_session_history')
    
    return redirect('counselor_session_history')

@login_required
@user_passes_test(is_counselor)
def student_profile(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    # Get related data
    appointments = Appointment.objects.filter(student=student).order_by('-date')
    sessions = GuidanceSession.objects.filter(student=student).order_by('-date')
    interviews = Interview.objects.filter(student=student).order_by('-date')
    
    context = {
        'student': student,
        'appointments': appointments,
        'sessions': sessions,
        'interviews': interviews,
    }
    return render(request, 'counselor/student_profile.html', context)

@login_required
@user_passes_test(is_counselor)
def create_interview(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    counselor = get_object_or_404(Counselor, user=request.user)
    
    if request.method == 'POST':
        # Handle form submission
        interview_type = request.POST.get('interview_type')
        notes = request.POST.get('notes')
        
        interview = Interview.objects.create(
            student=student,
            counselor=counselor,
            interview_type=interview_type,
            notes=notes,
            date=timezone.now()
        )
        
        messages.success(request, 'Interview form created successfully.')
        return redirect('student_profile', student_id=student.id)
    
    return render(request, 'counselor/create_interview.html', {
        'student': student
    })
