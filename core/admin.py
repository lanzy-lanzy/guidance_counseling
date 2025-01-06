
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Student, Counselor, GuidanceSession, Appointment, FollowUp, Interview, Report

class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Information'
    extra = 0

class CounselorInline(admin.StackedInline):
    model = Counselor
    can_delete = False
    verbose_name_plural = 'Counselor Information'
    extra = 0

class InterviewInline(admin.StackedInline):
    model = Interview
    can_delete = False
    extra = 0
    readonly_fields = ('date',)

class FollowUpInline(admin.StackedInline):
    model = FollowUp
    extra = 0

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'approval_status', 'is_active', 'profile_picture_preview', 'date_joined', 'view_details')
    list_filter = ('role', 'approval_status', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = ['approve_users', 'reject_users', 'activate_users', 'deactivate_users']
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture', 'profile_picture_preview')}),
        ('Role & Status', {'fields': ('role', 'approval_status', 'is_active')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.profile_picture.url)
        return "No picture"
    profile_picture_preview.short_description = 'Profile Picture'

    def view_details(self, obj):
        if obj.role == 'student':
            url = reverse('admin:core_student_change', args=[obj.student_profile.id])
        elif obj.role == 'counselor':
            url = reverse('admin:core_counselor_change', args=[obj.counselor_profile.id])
        else:
            return "-"
        return mark_safe(f'<a href="{url}">View {obj.role} details</a>')
    view_details.short_description = 'Profile Details'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'year', 'contact_number', 'session_count', 'last_session')
    list_filter = ('year', 'course')
    search_fields = ('user__username', 'user__email', 'course')
    raw_id_fields = ('user',)
    inlines = [InterviewInline]

    def session_count(self, obj):
        return obj.sessions.count()
    session_count.short_description = 'Total Sessions'

    def last_session(self, obj):
        last = obj.sessions.order_by('-date').first()
        return last.date if last else '-'
    last_session.short_description = 'Last Session'

@admin.register(GuidanceSession)
class GuidanceSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'counselor', 'session_type', 'date', 'status', 'duration_display')
    list_filter = ('session_type', 'status', 'date', 'counselor')
    search_fields = ('student__user__username', 'counselor__user__username', 'problem_statement')
    date_hierarchy = 'date'
    raw_id_fields = ('student', 'counselor')
    inlines = [FollowUpInline]
    readonly_fields = ('created_at', 'updated_at', 'duration_display')

    def duration_display(self, obj):
        if obj.duration:
            minutes = obj.duration.total_seconds() / 60
            return f"{int(minutes)} minutes"
        return "-"
    duration_display.short_description = 'Session Duration'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'counselor', 'date', 'time', 'status', 'created_at', 'has_session')
    list_filter = ('status', 'date', 'created_at')
    search_fields = ('student__user__username', 'counselor__user__username', 'purpose')
    date_hierarchy = 'date'
    raw_id_fields = ('student', 'counselor')
    actions = ['approve_appointments', 'decline_appointments']
    readonly_fields = ('created_at', 'updated_at')

    def has_session(self, obj):
        return hasattr(obj, 'session')
    has_session.boolean = True
    has_session.short_description = 'Session Created'

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'format', 'generated_by', 'generated_at', 'download_report')
    list_filter = ('report_type', 'format', 'generated_at')
    search_fields = ('name', 'generated_by__username')
    readonly_fields = ('generated_at', 'file')

    def download_report(self, obj):
        if obj.file:
            return mark_safe(f'<a href="{obj.file.url}">Download</a>')
        return "-"
    download_report.short_description = 'Download'

admin.site.register(Interview)
admin.site.register(FollowUp)
