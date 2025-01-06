from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Student, Appointment, GuidanceSession, Interview, Counselor
from datetime import datetime, timedelta

def is_student(user):
    return user.is_authenticated and user.role == 'student'

@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    student = get_object_or_404(Student, user=request.user)
    upcoming_appointments = Appointment.objects.filter(
        student=student,
        date__gte=timezone.now().date()
    ).order_by('date', 'time')[:5]
    
    recent_sessions = GuidanceSession.objects.filter(
        student=student
    ).order_by('-date')[:5]
    
    context = {
        'upcoming_appointments': upcoming_appointments,
        'recent_sessions': recent_sessions,
        'total_sessions': GuidanceSession.objects.filter(student=student).count(),
        'pending_appointments': Appointment.objects.filter(student=student, status='pending').count(),
        'completed_sessions': GuidanceSession.objects.filter(student=student, status='completed').count()
    }
    return render(request, 'student/dashboard.html', context)

@login_required
@user_passes_test(is_student)
def student_appointment_list(request):
    student = get_object_or_404(Student, user=request.user)
    appointments = Appointment.objects.filter(student=student).order_by('-date', '-time')
    counselors = Counselor.objects.all()
    
    # Add these specific querysets
    context = {
        'appointments': appointments,
        'counselors': counselors,
        'upcoming_appointments': appointments.filter(
            date__gte=timezone.now().date(),
            status__in=['pending', 'approved']  # Include both pending and approved
        ),
        'past_appointments': appointments.filter(
            date__lt=timezone.now().date()
        )
    }
    return render(request, 'student/appointments.html', context)

@login_required
@user_passes_test(is_student)
def student_session_history(request):
    student = get_object_or_404(Student, user=request.user)
    sessions = GuidanceSession.objects.filter(student=student).order_by('-date')
    return render(request, 'student/session_history.html', {'sessions': sessions})

@login_required
@user_passes_test(is_student)
def student_interview_forms(request):
    student = get_object_or_404(Student, user=request.user)
    interviews = Interview.objects.filter(student=student).order_by('-date')
    return render(request, 'student/interview_forms.html', {'interviews': interviews})

@login_required
@user_passes_test(is_student)
def student_counselor_list(request):
    counselors = Counselor.objects.all()
    return render(request, 'student/counselors.html', {'counselors': counselors})

@login_required
@user_passes_test(is_student)
def request_appointment(request):
    if request.method == 'POST':
        student = get_object_or_404(Student, user=request.user)
        counselor_id = request.POST.get('counselor')
        date = request.POST.get('date')
        time = request.POST.get('time')
        purpose = request.POST.get('purpose')
        
        counselor = get_object_or_404(Counselor, id=counselor_id)
        
        # Create appointment
        appointment = Appointment.objects.create(
            student=student,
            counselor=counselor,
            date=date,
            time=time,
            purpose=purpose,
            status='pending'
        )
        
        messages.success(request, 'Appointment request submitted successfully.')
        return redirect('student_appointment_list')
        
    counselors = Counselor.objects.all()
    context = {
        'counselors': counselors,
        'today': timezone.now().date()
    }
    return render(request, 'student/request_appointment.html', context)

@login_required
@user_passes_test(is_student)
def cancel_appointment(request, appointment_id):
    student = get_object_or_404(Student, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, student=student)
    
    if appointment.status == 'pending':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')
    else:
        messages.error(request, 'Cannot cancel this appointment.')
    
    return redirect('student_appointment_list')

@login_required
def student_profile(request):
    student = get_object_or_404(Student, user=request.user)
    
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            request.user.profile_picture = request.FILES['profile_picture']
        
        # Update user information
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.save()
        
        # Update student information
        student.course = request.POST.get('course')
        student.year = request.POST.get('year')
        student.contact_number = request.POST.get('contact_number')
        student.save()
        
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
        return redirect('student_profile')
    
    return render(request, 'student/profile.html', {'student': student})
