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
    appointments = Appointment.objects.filter(counselor=counselor)

    # Get current date for filtering upcoming appointments
    current_date = timezone.now().date()
    
    # Filter upcoming appointments
    if request.GET.get('status') == 'approved':
        appointments = appointments.filter(
            status='approved',
            date__gte=current_date
        ).order_by('date', 'time')

    context = {
        'appointments': appointments,
        'today_appointments': appointments.filter(date=current_date).count(),
        'pending_appointments': appointments.filter(status='pending').count(),
        'upcoming_appointments': appointments.filter(
            status='approved', 
            date__gte=current_date
        ).count(),
    }

    return render(request, 'counselor/appointments.html', context)
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
    
    session = GuidanceSession.objects.create(
        student=appointment.student,
        counselor=counselor,
        session_type='Interview',
        status='scheduled',
        appointment=appointment
    )
    
    session.start_session()
    appointment.status = 'completed'
    appointment.save()
    
    # Create interview with default/placeholder values for required fields
    interview = Interview.objects.create(
        student=appointment.student,
        counselor=counselor,
        session=session,
        address="To be updated",
        contact_number="To be updated",
        birth_date=appointment.student.user.date_joined.date(),  # Temporary default
        birth_place="To be updated",
        age=0,  # Will be updated in form
        civil_status="Single",  # Default value
        religion="To be updated",
        parents_marital_status="To be updated",
        elementary_school="To be updated",
        elementary_year_graduated="To be updated",
        high_school="To be updated",
        high_school_year_graduated="To be updated",
        reason_for_interview="To be updated",
        presenting_problem="To be updated",
        background_of_problem="To be updated"
    )
    
    return redirect('interview_form', interview_id=interview.id)
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

def interview_form(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    session = interview.session
    
    if request.method == 'POST':
        # Update interview details
        interview.time_started = request.POST.get('time_started')
        interview.time_ended = request.POST.get('time_ended')
        interview.reason_for_interview = request.POST.get('interview_reason')
        interview.presenting_problem = request.POST.get('problem_statement')
        interview.counselor_notes = request.POST.get('interview_notes')
        interview.recommendations = request.POST.get('recommendation')
        interview.save()
        
        # End the guidance session
        session.end_session(
            problem_statement=request.POST.get('problem_statement'),
            recommendations=request.POST.get('recommendation'),
            notes=request.POST.get('interview_notes')
        )
        
        messages.success(request, 'Interview form saved and session completed successfully.')
        return redirect('counselor_session_history')
        
    context = {
        'interview': interview,
        'student': interview.student,
        'session': session,
        'view_only': False
    }
    return render(request, 'counselor/interview_form.html', context)

def view_interview(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    context = {
        'interview': interview,
        'student': interview.student,
        'session': interview.session,
        'view_only': True
    }
    return render(request, 'counselor/interview_form.html', context)

@login_required
def counselor_profile(request):
    counselor = get_object_or_404(Counselor, user=request.user)
    
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            request.user.profile_picture = request.FILES['profile_picture']
        
        # Update user information
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.phone_number = request.POST.get('phone_number')
        request.user.save()
        
        # Update counselor information
        counselor.specialization = request.POST.get('specialization')
        counselor.bio = request.POST.get('bio')
        counselor.save()
        
        # Handle password change
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        if current_password and new_password:
            if request.user.check_password(current_password):
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, 'Password updated successfully.')
            else:
                messages.error(request, 'Current password is incorrect.')
        
        messages.success(request, 'Profile updated successfully.')
        return redirect('counselor_profile')
    
    return render(request, 'counselor/profile.html', {'counselor': counselor})
