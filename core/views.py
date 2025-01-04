from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, TemplateView
from django.urls import reverse
from django.conf import settings
from .forms import UserRegistrationForm, AppointmentForm, InterviewForm
from .models import Student, Counselor, Appointment, GuidanceSession, FollowUp, Interview, Report
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import json
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
import xlsxwriter
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
import csv

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account is not active. Please contact the administrator.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'auth/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User needs admin approval
            user.approval_status = 'pending'
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            
            # Create the role-specific profile
            if user.role == 'Student':
                Student.objects.create(
                    user=user,
                    course=request.POST.get('course', ''),
                    year=request.POST.get('year', 1)
                )
            elif user.role == 'Counselor':
                Counselor.objects.create(
                    user=user,
                    email=user.email
                )
            
            messages.success(request, 'Registration successful! Please wait for admin approval to login.')
            return redirect('login')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    from django.utils import timezone
    from datetime import datetime, timedelta
    today = timezone.now().date()

    context = {
        'user': request.user,
        'role': request.user.role,
    }

    if request.user.role == 'Counselor':
        try:
            # Get counselor profile
            counselor = request.user.counselor_profile

            # Get today's sessions count
            context['today_sessions_count'] = Appointment.objects.filter(
                counselor=counselor,
                date=today,
                status='approved'
            ).count()

            # Get total active students
            context['total_students'] = Student.objects.filter(
                user__is_active=True
            ).count()

            # Get pending appointments
            context['pending_appointments'] = Appointment.objects.filter(
                counselor=counselor,
                status='pending'
            ).count()

            # Get recent appointments (last 5)
            context['recent_appointments'] = Appointment.objects.filter(
                counselor=counselor
            ).order_by('-date', '-time')[:5]

        except Counselor.DoesNotExist:
            messages.error(request, 'Counselor profile not found. Please contact the administrator.')
            logout(request)
            return redirect('login')

    else:  # Student view
        try:
            # Get student profile
            student = request.user.student_profile

            # Get next appointment
            context['next_appointment'] = Appointment.objects.filter(
                student=student,
                date__gte=today,
                status='approved'
            ).order_by('date', 'time').first()

            # Get total completed sessions
            context['total_sessions'] = GuidanceSession.objects.filter(
                student=student
            ).count()

            # Get pending follow-ups
            context['pending_followups'] = FollowUp.objects.filter(
                session__student=student,
                completed=False,
                followup_date__gte=today
            ).count()

            # Get recent sessions (last 5)
            context['recent_sessions'] = GuidanceSession.objects.filter(
                student=student
            ).order_by('-date')[:5]

        except Student.DoesNotExist:
            messages.error(request, 'Student profile not found. Please contact the administrator.')
            logout(request)
            return redirect('login')

    return render(request, 'dashboard.html', context)

@login_required
def schedule_session(request):
    if request.user.role != 'Student':
        messages.error(request, 'Only students can schedule counseling sessions.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.student = request.user.student_profile
            appointment.save()
            messages.success(request, 'Session scheduled successfully! Please wait for counselor confirmation.')
            return redirect('dashboard')
    else:
        form = AppointmentForm()
    
    return render(request, 'schedule_session.html', {'form': form})

@login_required
def appointment_list(request):
    context = {}
    if request.user.role == 'Student':
        appointments = Appointment.objects.filter(student=request.user.student_profile)
        context['is_counselor'] = False
    elif request.user.role == 'Counselor':
        appointments = Appointment.objects.filter(counselor=request.user.counselor_profile)
        context['is_counselor'] = True
    else:
        messages.error(request, 'Invalid user role')
        return redirect('dashboard')
    
    # Filter by status if specified
    status = request.GET.get('status')
    if status in ['pending', 'approved', 'declined']:
        appointments = appointments.filter(status=status)
    
    context['appointments'] = appointments
    context['current_status'] = status  # Pass the current status to the template
    return render(request, 'appointments/appointment_list.html', context)

@login_required
def update_appointment_status(request, appointment_id):
    if request.user.role != 'Counselor':
        messages.error(request, 'Only counselors can approve or decline appointments.')
        return redirect('dashboard')
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('appointment_list')

    try:
        appointment = Appointment.objects.get(id=appointment_id, counselor=request.user.counselor_profile)
        new_status = request.POST.get('status')
        
        if new_status in ['approved', 'declined']:
            appointment.status = new_status
            appointment.save()
            messages.success(request, f'Appointment {new_status} successfully.')
        else:
            messages.error(request, 'Invalid status.')
        return redirect('appointment_list')
        
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('appointment_list')

@login_required
def start_guidance_session(request, appointment_id):
    if request.user.role != 'Counselor':
        messages.error(request, 'Only counselors can start guidance sessions.')
        return redirect('appointment_list')
    
    try:
        appointment = Appointment.objects.get(id=appointment_id, counselor=request.user.counselor_profile, status='approved')
        
        # Check if session already exists for this appointment
        existing_session = GuidanceSession.objects.filter(appointment=appointment).first()
        if existing_session:
            messages.warning(request, 'A session already exists for this appointment.')
            return redirect('guidance_session_detail', session_id=existing_session.id)
        
        if request.method == 'POST':
            session_type = request.POST.get('session_type')
            if session_type not in dict(GuidanceSession.SESSION_TYPE_CHOICES):
                messages.error(request, 'Invalid session type.')
                return redirect('appointment_list')
            
            # Create new guidance session
            session = GuidanceSession.objects.create(
                student=appointment.student,
                counselor=appointment.counselor,
                session_type=session_type,
                appointment=appointment,
                status='scheduled'
            )
            
            # Start the session immediately
            session.start_session()
            
            messages.success(request, 'Guidance session started successfully.')
            return redirect('guidance_session_detail', session_id=session.id)
        
        return render(request, 'counseling/start_session.html', {'appointment': appointment})
        
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found or not approved.')
        return redirect('appointment_list')

@login_required
def start_followup_session(request, session_id):
    if request.user.role != 'Counselor':
        messages.error(request, 'Only counselors can start follow-up sessions.')
        return redirect('session_history')
    
    try:
        # Get the original session
        original_session = GuidanceSession.objects.get(id=session_id)
        
        # Check if this counselor is authorized
        if request.user.counselor_profile != original_session.counselor:
            messages.error(request, 'You are not authorized to start this follow-up session.')
            return redirect('session_history')
        
        # Check if the original session is completed
        if original_session.status != 'completed':
            messages.error(request, 'Can only create follow-ups for completed sessions.')
            return redirect('guidance_session_detail', session_id=session_id)
        
        # Check if a follow-up session already exists
        if hasattr(original_session, 'followup'):
            followup = original_session.followup
            if not followup.completed:
                # If there's an uncompleted follow-up, create a new session for it
                existing_followup_session = GuidanceSession.objects.filter(
                    student=original_session.student,
                    counselor=original_session.counselor,
                    session_type='Follow-Up',
                    status='scheduled'
                ).first()
                
                if existing_followup_session:
                    # Start the existing follow-up session
                    existing_followup_session.start_session()
                    messages.success(request, 'Follow-up session started successfully.')
                    return redirect('guidance_session_detail', session_id=existing_followup_session.id)
                else:
                    # Create and start a new follow-up session
                    followup_session = GuidanceSession.objects.create(
                        student=original_session.student,
                        counselor=original_session.counselor,
                        session_type='Follow-Up',
                        status='scheduled'
                    )
                    followup_session.start_session()
                    messages.success(request, 'Follow-up session started successfully.')
                    return redirect('guidance_session_detail', session_id=followup_session.id)
            else:
                messages.error(request, 'The follow-up for this session has already been completed.')
                return redirect('guidance_session_detail', session_id=session_id)
        else:
            messages.error(request, 'No follow-up scheduled for this session.')
            return redirect('guidance_session_detail', session_id=session_id)
            
    except GuidanceSession.DoesNotExist:
        messages.error(request, 'Session not found.')
        return redirect('session_history')

@login_required
def guidance_session_detail(request, session_id):
    try:
        session = GuidanceSession.objects.get(id=session_id)
        
        # Ensure only the counselor and student involved can access the session
        if request.user.role == 'Counselor' and request.user.counselor_profile != session.counselor:
            messages.error(request, 'You do not have permission to view this session.')
            return redirect('session_history')
        elif request.user.role == 'Student' and request.user.student_profile != session.student:
            messages.error(request, 'You do not have permission to view this session.')
            return redirect('session_history')
        
        if request.method == 'POST':
            if request.user.role != 'Counselor':
                messages.error(request, 'Only counselors can update sessions.')
                return redirect('guidance_session_detail', session_id=session.id)

            # Handle session end
            if 'end_session' in request.POST:
                if session.status != 'in_progress':
                    messages.error(request, 'Can only end sessions that are in progress.')
                    return redirect('guidance_session_detail', session_id=session.id)

                session.end_session(
                    problem_statement=request.POST.get('problem_statement', ''),
                    recommendations=request.POST.get('recommendations', ''),
                    notes=request.POST.get('notes', ''),
                    action_items=request.POST.get('action_items', ''),
                    next_steps=request.POST.get('next_steps', '')
                )
                
                # Create follow-up if requested
                if request.POST.get('schedule_followup'):
                    followup_date = request.POST.get('followup_date')
                    if followup_date:
                        FollowUp.objects.create(
                            session=session,
                            followup_date=followup_date,
                            followup_notes=request.POST.get('followup_notes', '')
                        )
                        messages.success(request, 'Follow-up scheduled successfully.')
                
                messages.success(request, 'Guidance session ended successfully.')
                return redirect('completed_sessions')
            
            # Handle session cancellation
            elif 'cancel_session' in request.POST:
                if session.status not in ['scheduled', 'in_progress']:
                    messages.error(request, 'Cannot cancel a completed or already cancelled session.')
                    return redirect('guidance_session_detail', session_id=session.id)

                session.cancel_session()
                messages.success(request, 'Session cancelled successfully.')
                return redirect('session_history')
            
            # Handle session start
            elif 'start_session' in request.POST:
                if session.status != 'scheduled':
                    messages.error(request, 'Can only start scheduled sessions.')
                    return redirect('guidance_session_detail', session_id=session.id)

                session.start_session()
                messages.success(request, 'Session started successfully.')
                return redirect('guidance_session_detail', session_id=session.id)

        context = {
            'session': session,
            'can_modify': request.user.role == 'Counselor' and request.user.counselor_profile == session.counselor
        }
        
        return render(request, 'counseling/session_detail.html', context)
        
    except GuidanceSession.DoesNotExist:
        messages.error(request, 'Session not found.')
        return redirect('session_history')

@login_required
def completed_sessions(request):
    # Get the filter parameters
    session_type = request.GET.get('type', '')
    date_filter = request.GET.get('date', '')
    status_filter = request.GET.get('status', 'completed')  # Default to showing completed sessions

    # Base query for sessions
    if request.user.role == 'Counselor':
        sessions = GuidanceSession.objects.filter(counselor=request.user.counselor_profile)
    else:  # Student
        sessions = GuidanceSession.objects.filter(student=request.user.student_profile)

    # Apply filters
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if session_type:
        sessions = sessions.filter(session_type=session_type)
    if date_filter:
        sessions = sessions.filter(date=date_filter)

    # Order by most recent first
    sessions = sessions.order_by('-created_at')

    context = {
        'sessions': sessions,
        'session_types': GuidanceSession.SESSION_TYPE_CHOICES,
        'status_choices': GuidanceSession.STATUS_CHOICES,
        'current_filters': {
            'type': session_type,
            'date': date_filter,
            'status': status_filter
        }
    }
    return render(request, 'counseling/completed_sessions.html', context)

@login_required
def session_history(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    session_type = request.GET.get('type', '')
    date_filter = request.GET.get('date', '')
    page = request.GET.get('page', 1)

    # Base query
    if request.user.role == 'Counselor':
        sessions = GuidanceSession.objects.filter(counselor=request.user.counselor_profile)
    else:  # Student
        sessions = GuidanceSession.objects.filter(student=request.user.student_profile)

    # Apply filters
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if session_type:
        sessions = sessions.filter(session_type=session_type)
    if date_filter:
        sessions = sessions.filter(date=date_filter)

    # Order by most recent first
    sessions = sessions.order_by('-created_at')

    # Pagination
    paginator = Paginator(sessions, 10)  # Show 10 sessions per page
    try:
        sessions = paginator.page(page)
    except PageNotAnInteger:
        sessions = paginator.page(1)
    except EmptyPage:
        sessions = paginator.page(paginator.num_pages)

    context = {
        'sessions': sessions,
        'session_types': GuidanceSession.SESSION_TYPE_CHOICES,
        'status_choices': GuidanceSession.STATUS_CHOICES,
        'current_filters': {
            'type': session_type,
            'date': date_filter,
            'status': status_filter
        }
    }
    return render(request, 'counseling/session_history.html', context)

@login_required
def reschedule_appointment(request, appointment_id):
    if request.user.role != 'Counselor':
        messages.error(request, 'Only counselors can reschedule appointments.')
        return redirect('appointment_list')
    
    appointment = Appointment.objects.get(id=appointment_id)
    
    if request.method == 'POST':
        new_date = request.POST.get('date')
        new_time = request.POST.get('time')
        
        if new_date and new_time:
            appointment.date = new_date
            appointment.time = new_time
            appointment.save()
            
            messages.success(request, 'Appointment rescheduled successfully.')
            return redirect('appointment_list')
        else:
            messages.error(request, 'Please provide both date and time.')
    
    context = {
        'appointment': appointment
    }
    return render(request, 'appointments/reschedule_appointment.html', context)

@login_required
def create_interview_form(request, student_id):
    student = Student.objects.get(id=student_id)
    
    if request.method == 'POST':
        try:
            interview_form = Interview(
                student=student,
                counselor=request.user.counselor_profile,
                address=request.POST.get('address'),
                contact_number=request.POST.get('contact_number'),
                birth_date=request.POST.get('birth_date'),
                birth_place=request.POST.get('birth_place'),
                age=request.POST.get('age'),
                civil_status=request.POST.get('civil_status'),
                religion=request.POST.get('religion'),
                father_name=request.POST.get('father_name'),
                father_occupation=request.POST.get('father_occupation'),
                father_education=request.POST.get('father_education'),
                mother_name=request.POST.get('mother_name'),
                mother_occupation=request.POST.get('mother_occupation'),
                mother_education=request.POST.get('mother_education'),
                parents_marital_status=request.POST.get('parents_marital_status'),
                elementary_school=request.POST.get('elementary_school'),
                elementary_year_graduated=request.POST.get('elementary_year_graduated'),
                high_school=request.POST.get('high_school'),
                high_school_year_graduated=request.POST.get('high_school_year_graduated'),
                college_school=request.POST.get('college_school'),
                college_course=request.POST.get('college_course'),
                reason_for_interview=request.POST.get('reason_for_interview'),
                presenting_problem=request.POST.get('presenting_problem'),
                background_of_problem=request.POST.get('background_of_problem'),
                counselor_notes=request.POST.get('counselor_notes'),
                recommendations=request.POST.get('recommendations'),
                follow_up_needed=request.POST.get('follow_up_needed') == 'on'
            )
            interview_form.save()
            messages.success(request, 'Interview form has been saved successfully.')
            return redirect('student_detail', pk=student_id)
        except Exception as e:
            messages.error(request, f'Error saving interview form: {str(e)}')
            return redirect('create_interview_form', student_id=student_id)
    
    return render(request, 'counseling/interview_form.html', {
        'student': student
    })

@login_required
def view_interview_form(request, form_id):
    interview_form = Interview.objects.get(id=form_id)
    return render(request, 'counseling/interview_form.html', {
        'form': interview_form,
        'student': interview_form.student,
        'view_only': True
    })

class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'students.html'
    context_object_name = 'students'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique courses for the filter dropdown
        context['courses'] = Student.objects.values_list('course', flat=True).distinct()
        return context

class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'students/student_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get student's counseling sessions
        context['sessions'] = GuidanceSession.objects.filter(student=self.object).order_by('-date')
        return context

class EditStudentView(LoginRequiredMixin, UpdateView):
    model = Student
    template_name = 'students/edit_student.html'
    fields = ['course', 'year', 'contact_number', 'reason_for_referral']
    context_object_name = 'student'

    def get_success_url(self):
        return reverse('student_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Student profile updated successfully.')
        return super().form_valid(form)

class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/reports_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic statistics
        context['total_students'] = Student.objects.count()
        context['total_sessions'] = GuidanceSession.objects.count()
        context['active_cases'] = GuidanceSession.objects.filter(status='ongoing').count()
        
        # Calculate completion rate
        completed_sessions = GuidanceSession.objects.filter(status='completed').count()
        total_sessions = context['total_sessions']
        context['completion_rate'] = round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0)

        # Get recent reports
        context['recent_reports'] = Report.objects.all().order_by('-generated_at')[:5]

        # Session types distribution
        session_types = GuidanceSession.objects.values('session_type').annotate(count=Count('id'))
        context['session_types_labels'] = json.dumps([st['session_type'] for st in session_types])
        context['session_types_data'] = json.dumps([st['count'] for st in session_types])

        # Monthly trend (last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_sessions = GuidanceSession.objects.filter(
            date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        context['monthly_labels'] = json.dumps([s['month'].strftime('%B %Y') for s in monthly_sessions])
        context['monthly_data'] = json.dumps([s['count'] for s in monthly_sessions])

        # Course distribution
        course_distribution = Student.objects.values('course').annotate(count=Count('id'))
        context['course_labels'] = json.dumps([c['course'] for c in course_distribution])
        context['course_data'] = json.dumps([c['count'] for c in course_distribution])

        # Recent sessions
        context['recent_sessions'] = GuidanceSession.objects.select_related(
            'student', 'student__user'
        ).order_by('-date')[:10]

        return context

@login_required
def export_report_excel(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    # Create response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=guidance_report.xlsx'

    # Create workbook and worksheet
    workbook = xlsxwriter.Workbook(response)
    worksheet = workbook.add_worksheet()

    # Add headers
    headers = ['Student Name', 'Course', 'Session Type', 'Date', 'Status']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Add data
    sessions = GuidanceSession.objects.select_related('student', 'student__user').all()
    for row, session in enumerate(sessions, start=1):
        worksheet.write(row, 0, session.student.user.get_full_name())
        worksheet.write(row, 1, session.student.course)
        worksheet.write(row, 2, session.session_type)
        worksheet.write(row, 3, session.date.strftime('%Y-%m-%d'))
        worksheet.write(row, 4, session.status)

    workbook.close()
    return response

@login_required
def export_report_pdf(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=guidance_report.pdf'

    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Add title
    title = "Guidance Counseling Report"
    elements.append(Paragraph(title, getSampleStyleSheet()['Title']))

    # Prepare data for table
    data = [['Student Name', 'Course', 'Session Type', 'Date', 'Status']]
    sessions = GuidanceSession.objects.select_related('student', 'student__user').all()
    for session in sessions:
        data.append([
            session.student.user.get_full_name(),
            session.student.course,
            session.session_type,
            session.date.strftime('%Y-%m-%d'),
            session.status
        ])

    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)

    # Build PDF
    doc.build(elements)
    return response

@login_required
def generate_report(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        date_range = request.POST.get('date_range')
        format_type = request.POST.get('format')

        # Handle custom date range
        start_date = None
        end_date = None
        if date_range == 'custom':
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            if not start_date or not end_date:
                messages.error(request, 'Please provide both start and end dates for custom range.')
                return redirect('reports_dashboard')

        else:
            # Calculate date range based on selection
            end_date = timezone.now().date()
            if date_range == 'this_week':
                start_date = end_date - timedelta(days=7)
            elif date_range == 'this_month':
                start_date = end_date.replace(day=1)
            elif date_range == 'last_month':
                last_month = end_date.replace(day=1) - timedelta(days=1)
                start_date = last_month.replace(day=1)
                end_date = last_month
            elif date_range == 'this_year':
                start_date = end_date.replace(month=1, day=1)

        # Generate report name
        report_name = f"{report_type}_{date_range}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Create report object
            report = Report.objects.create(
                name=report_name,
                report_type=report_type,
                format=format_type,
                generated_by=request.user,
                start_date=start_date,
                end_date=end_date
            )

            # Generate report based on type
            if format_type == 'pdf':
                file_path = generate_pdf_report(report_type, start_date, end_date)
            elif format_type == 'excel':
                file_path = generate_excel_report(report_type, start_date, end_date)
            else:  # CSV
                file_path = generate_csv_report(report_type, start_date, end_date)

            # Save the generated file to the report object
            with open(file_path, 'rb') as f:
                report.file.save(f"{report_name}.{format_type}", f)

            messages.success(request, 'Report generated successfully.')
            return redirect('view_report', report_id=report.id)

        except Exception as e:
            messages.error(request, f'Error generating report: {str(e)}')
            return redirect('reports_dashboard')

    return redirect('reports_dashboard')

@login_required
def view_report(request, report_id):
    try:
        report = Report.objects.get(id=report_id)
        context = {
            'report': report,
            'download_url': report.file.url if report.file else None,
        }
        return render(request, 'reports/view_report.html', context)
    except Report.DoesNotExist:
        messages.error(request, 'Report not found.')
        return redirect('reports_dashboard')

def generate_pdf_report(report_type, start_date, end_date):
    # Create a temporary file path
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f'report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf')

    # Create PDF document
    doc = SimpleDocTemplate(temp_file, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Add title
    title = Paragraph(f"Guidance Counseling Report - {report_type}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))

    # Add date range
    date_range_text = f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    date_range = Paragraph(date_range_text, styles['Normal'])
    elements.append(date_range)
    elements.append(Spacer(1, 20))

    # Generate report data based on type
    if report_type == 'student_summary':
        data = [['Student Name', 'Course', 'Year', 'Total Sessions', 'Status']]
        students = Student.objects.all()
        for student in students:
            sessions = GuidanceSession.objects.filter(
                student=student,
                date__range=[start_date, end_date]
            ).count()
            data.append([
                f"{student.user.get_full_name()}",
                student.course,
                student.year,
                sessions,
                'Active' if sessions > 0 else 'Inactive'
            ])

    elif report_type == 'session_analytics':
        data = [['Date', 'Total Sessions', 'Completed', 'Ongoing']]
        sessions = GuidanceSession.objects.filter(date__range=[start_date, end_date])
        dates = sessions.dates('date', 'day')
        for date in dates:
            day_sessions = sessions.filter(date=date)
            data.append([
                date.strftime('%Y-%m-%d'),
                day_sessions.count(),
                day_sessions.filter(status='completed').count(),
                day_sessions.filter(status='ongoing').count()
            ])

    elif report_type == 'counselor_performance':
        data = [['Counselor Name', 'Total Sessions', 'Completed', 'Success Rate']]
        counselors = Counselor.objects.all()
        for counselor in counselors:
            sessions = GuidanceSession.objects.filter(
                counselor=counselor,
                date__range=[start_date, end_date]
            )
            total = sessions.count()
            completed = sessions.filter(status='completed').count()
            success_rate = (completed / total * 100) if total > 0 else 0
            data.append([
                counselor.user.get_full_name(),
                total,
                completed,
                f"{success_rate:.1f}%"
            ])

    else:  # case_management
        data = [['Case ID', 'Student', 'Status', 'Sessions', 'Last Updated']]
        sessions = GuidanceSession.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('student')
        
        for session in sessions:
            data.append([
                f"CASE-{session.id}",
                session.student.user.get_full_name(),
                session.status.title(),
                session.followup_set.count(),
                session.updated_at.strftime('%Y-%m-%d')
            ])

    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)

    # Build PDF
    doc.build(elements)
    return temp_file

def generate_excel_report(report_type, start_date, end_date):
    # Create a temporary file path
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f'report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx')

    # Create workbook and worksheet
    workbook = xlsxwriter.Workbook(temp_file)
    worksheet = workbook.add_worksheet()

    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4B5563',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    cell_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })

    # Write title
    worksheet.merge_range('A1:E1', f'Guidance Counseling Report - {report_type}', header_format)
    worksheet.merge_range('A2:E2', f'Period: {start_date.strftime("%B %d, %Y")} - {end_date.strftime("%B %d, %Y")}', cell_format)

    # Generate report data based on type
    if report_type == 'student_summary':
        headers = ['Student Name', 'Course', 'Year', 'Total Sessions', 'Status']
        row = 3
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        students = Student.objects.all()
        for student in students:
            row += 1
            sessions = GuidanceSession.objects.filter(
                student=student,
                date__range=[start_date, end_date]
            ).count()
            data = [
                student.user.get_full_name(),
                student.course,
                student.year,
                sessions,
                'Active' if sessions > 0 else 'Inactive'
            ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value, cell_format)

    elif report_type == 'session_analytics':
        headers = ['Date', 'Total Sessions', 'Completed', 'Ongoing']
        row = 3
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        sessions = GuidanceSession.objects.filter(date__range=[start_date, end_date])
        dates = sessions.dates('date', 'day')
        for date in dates:
            row += 1
            day_sessions = sessions.filter(date=date)
            data = [
                date.strftime('%Y-%m-%d'),
                day_sessions.count(),
                day_sessions.filter(status='completed').count(),
                day_sessions.filter(status='ongoing').count()
            ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value, cell_format)

    elif report_type == 'counselor_performance':
        headers = ['Counselor Name', 'Total Sessions', 'Completed', 'Success Rate']
        row = 3
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        counselors = Counselor.objects.all()
        for counselor in counselors:
            row += 1
            sessions = GuidanceSession.objects.filter(
                counselor=counselor,
                date__range=[start_date, end_date]
            )
            total = sessions.count()
            completed = sessions.filter(status='completed').count()
            success_rate = (completed / total * 100) if total > 0 else 0
            data = [
                counselor.user.get_full_name(),
                total,
                completed,
                f"{success_rate:.1f}%"
            ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value, cell_format)

    else:  # case_management
        headers = ['Case ID', 'Student', 'Status', 'Sessions', 'Last Updated']
        row = 3
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        sessions = GuidanceSession.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('student')
        
        for session in sessions:
            row += 1
            data = [
                f"CASE-{session.id}",
                session.student.user.get_full_name(),
                session.status.title(),
                session.followup_set.count(),
                session.updated_at.strftime('%Y-%m-%d')
            ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value, cell_format)

    # Auto-adjust column widths
    for col in range(len(headers)):
        worksheet.set_column(col, col, 15)

    workbook.close()
    return temp_file

def generate_csv_report(report_type, start_date, end_date):
    # Create a temporary file path
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f'report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv')

    with open(temp_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write headers based on report type
        if report_type == 'student_summary':
            writer.writerow(['Student Name', 'Course', 'Year', 'Total Sessions', 'Status'])
            students = Student.objects.all()
            for student in students:
                sessions = GuidanceSession.objects.filter(
                    student=student,
                    date__range=[start_date, end_date]
                ).count()
                writer.writerow([
                    student.user.get_full_name(),
                    student.course,
                    student.year,
                    sessions,
                    'Active' if sessions > 0 else 'Inactive'
                ])

        elif report_type == 'session_analytics':
            writer.writerow(['Date', 'Total Sessions', 'Completed', 'Ongoing'])
            sessions = GuidanceSession.objects.filter(date__range=[start_date, end_date])
            dates = sessions.dates('date', 'day')
            for date in dates:
                day_sessions = sessions.filter(date=date)
                writer.writerow([
                    date.strftime('%Y-%m-%d'),
                    day_sessions.count(),
                    day_sessions.filter(status='completed').count(),
                    day_sessions.filter(status='ongoing').count()
                ])

        elif report_type == 'counselor_performance':
            writer.writerow(['Counselor Name', 'Total Sessions', 'Completed', 'Success Rate'])
            counselors = Counselor.objects.all()
            for counselor in counselors:
                sessions = GuidanceSession.objects.filter(
                    counselor=counselor,
                    date__range=[start_date, end_date]
                )
                total = sessions.count()
                completed = sessions.filter(status='completed').count()
                success_rate = (completed / total * 100) if total > 0 else 0
                writer.writerow([
                    counselor.user.get_full_name(),
                    total,
                    completed,
                    f"{success_rate:.1f}%"
                ])

        else:  # case_management
            writer.writerow(['Case ID', 'Student', 'Status', 'Sessions', 'Last Updated'])
            sessions = GuidanceSession.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('student')
            
            for session in sessions:
                writer.writerow([
                    f"CASE-{session.id}",
                    session.student.user.get_full_name(),
                    session.status.title(),
                    session.followup_set.count(),
                    session.updated_at.strftime('%Y-%m-%d')
                ])

    return temp_file