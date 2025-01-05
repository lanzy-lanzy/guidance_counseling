from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import User, Student, Counselor, Appointment
from datetime import datetime
from django.db.models import Q
from .forms import UserForm

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'admin')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    try:
        total_users = User.objects.count()
        active_students = Student.objects.filter(user__is_active=True).count()
        active_counselors = Counselor.objects.filter(user__is_active=True).count()
        pending_approvals = User.objects.filter(approval_status='pending').count()
        
        # Get recent users
        recent_users = User.objects.order_by('-date_joined')[:5]
        
        # Get upcoming appointments
        upcoming_appointments = Appointment.objects.filter(
            date__gte=datetime.now()
        ).order_by('date')[:5]
        
        context = {
            'total_users': total_users,
            'active_students': active_students,
            'active_counselors': active_counselors,
            'pending_approvals': pending_approvals,
            'recent_users': recent_users,
            'upcoming_appointments': upcoming_appointments,
        }
        return render(request, 'admin/dashboard.html', context)
    except Exception as e:
        messages.error(request, f'Error loading dashboard: {str(e)}')
        return redirect('home')

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin/users.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def admin_add_user(request):
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'User created successfully')
            return redirect('admin_users')
    else:
        form = UserForm()
    return render(request, 'admin/add_user.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def admin_edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save()
            if form.cleaned_data.get('password'):
                user.set_password(form.cleaned_data['password'])
                user.save()
            messages.success(request, 'User updated successfully')
            return redirect('admin_users')
    else:
        form = UserForm(instance=user)
    return render(request, 'admin/edit_user.html', {'form': form, 'user': user})

@login_required
@user_passes_test(is_admin)
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully')
        return redirect('admin_users')
    return render(request, 'admin/delete_user.html', {'user': user})

@login_required
@user_passes_test(is_admin)
def admin_approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.approval_status = 'approved'
    user.is_active = True
    user.save()
    messages.success(request, f'User {user.username} has been approved')
    return redirect('admin_users')

@login_required
@user_passes_test(is_admin)
def admin_students(request):
    students = Student.objects.select_related('user').all()
    return render(request, 'admin/students.html', {'students': students})

@login_required
@user_passes_test(is_admin)
def admin_counselors(request):
    counselors = Counselor.objects.select_related('user').all()
    return render(request, 'admin/counselors.html', {'counselors': counselors})

@login_required
@user_passes_test(is_admin)
def admin_appointments(request):
    appointments = Appointment.objects.select_related('student', 'counselor').all()
    return render(request, 'admin/appointments.html', {'appointments': appointments})

@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    return render(request, 'admin/reports.html')

@login_required
@user_passes_test(is_admin)
def admin_settings(request):
    return render(request, 'admin/settings.html')
