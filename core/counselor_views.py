from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView
from django.contrib import messages
from .models import Appointment, Student, GuidanceSession, Interview, Counselor, FollowUp
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
    appointments = Appointment.objects.all().order_by('-date', '-time')

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
    
    # Create a new guidance session
    session = GuidanceSession.objects.create(
        student=appointment.student,
        counselor=counselor,
        session_type='Interview',
        status='in_progress',
        appointment=appointment,
        date=timezone.now().date(),
        time_started=timezone.now()
    )
    
    # Create interview with default values
    interview = Interview.objects.create(
        session=session,
        student=appointment.student,
        counselor=counselor,
        date=timezone.now().date(),
        address="",
        contact_number="",
        birth_date=appointment.student.user.date_joined.date(),  # Temporary default
        birth_place="",
        age=0,  # Will be updated in form
        civil_status="Single",  # Default value
        religion="",
        parents_marital_status="",
        elementary_school="",
        elementary_year_graduated="",
        high_school="",
        high_school_year_graduated="",
        reason_for_interview=appointment.purpose,
        presenting_problem="",
        background_of_problem=""
    )
    
    # Update appointment status
    appointment.status = 'completed'
    appointment.save()
    
    messages.success(request, 'Session started successfully.')
    return redirect('interview_form', interview_id=interview.id)

@login_required
@user_passes_test(is_counselor)
def interview_form(request, interview_id):
    counselor = get_object_or_404(Counselor, user=request.user)
    interview = get_object_or_404(Interview, id=interview_id, counselor=counselor)
    session = interview.session

    # Prevent accessing completed interviews in edit mode
    if session.status == 'completed':
        return redirect('view_interview', interview_id=interview.id)
    
    if request.method == 'POST':
        try:
            # Prevent duplicate submissions
            if session.status == 'completed':
                messages.warning(request, 'This interview has already been completed.')
                return redirect('view_interview', interview_id=interview.id)

            # Update interview details
            interview.address = request.POST.get('address', '')
            interview.contact_number = request.POST.get('contact_number', '')
            interview.birth_date = request.POST.get('birth_date')
            interview.birth_place = request.POST.get('birth_place', '')
            interview.age = int(request.POST.get('age', 0))
            interview.civil_status = request.POST.get('civil_status', 'Single')
            interview.religion = request.POST.get('religion', '')
            
            # Family Background
            interview.father_name = request.POST.get('father_name', '')
            interview.father_occupation = request.POST.get('father_occupation', '')
            interview.father_education = request.POST.get('father_education', '')
            interview.mother_name = request.POST.get('mother_name', '')
            interview.mother_occupation = request.POST.get('mother_occupation', '')
            interview.mother_education = request.POST.get('mother_education', '')
            interview.parents_marital_status = request.POST.get('parents_marital_status', '')
            
            # Educational Background
            interview.elementary_school = request.POST.get('elementary_school', '')
            interview.elementary_year_graduated = request.POST.get('elementary_year_graduated', '')
            interview.high_school = request.POST.get('high_school', '')
            interview.high_school_year_graduated = request.POST.get('high_school_year_graduated', '')
            
            # Interview Details
            interview.reason_for_interview = request.POST.get('reason_for_interview', '')
            interview.presenting_problem = request.POST.get('presenting_problem', '')
            interview.background_of_problem = request.POST.get('background_of_problem', '')
            interview.counselor_notes = request.POST.get('counselor_notes', '')
            interview.recommendations = request.POST.get('recommendations', '')
            interview.follow_up_needed = request.POST.get('follow_up_needed') == 'on'
            interview.save()

            # Update session status and details
            session.status = 'completed'
            session.time_ended = timezone.now()
            session.problem_statement = interview.presenting_problem
            session.recommendations = interview.recommendations
            session.notes = interview.counselor_notes
            session.save()

            # Create follow-up if needed
            if interview.follow_up_needed:
                follow_up_date = timezone.now() + timezone.timedelta(days=14)  # Default to 2 weeks
                FollowUp.objects.create(
                    session=session,
                    followup_date=follow_up_date,
                    followup_notes="Follow-up session scheduled"
                )

            messages.success(request, 'Interview form completed successfully.')
            return redirect('view_interview', interview_id=interview.id)
            
        except Exception as e:
            messages.error(request, f'An error occurred while saving the form: {str(e)}')
            return redirect('interview_form', interview_id=interview.id)
    
    context = {
        'interview': interview,
        'student': interview.student,
        'view_only': False
    }
    return render(request, 'counselor/interview_form.html', context)

@login_required
@user_passes_test(is_counselor)
def view_interview(request, interview_id):
    counselor = get_object_or_404(Counselor, user=request.user)
    interview = get_object_or_404(Interview, id=interview_id, counselor=counselor)
    context = {
        'interview': interview,
        'student': interview.student,
        'view_only': True
    }
    return render(request, 'counselor/interview_form.html', context)

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
