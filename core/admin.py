from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Student, Counselor, GuidanceSession, Appointment, FollowUp

class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Information'

class CounselorInline(admin.StackedInline):
    model = Counselor
    can_delete = False
    verbose_name_plural = 'Counselor Information'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'approval_status', 'is_active', 'profile_picture_preview', 'date_joined')
    list_filter = ('role', 'approval_status', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = ['approve_users', 'reject_users', 'activate_users', 'deactivate_users']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'profile_picture')}),
        ('Role & Status', {'fields': ('role', 'approval_status', 'is_active')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def get_inlines(self, request, obj=None):
        if obj:
            if obj.role == 'Student':
                return [StudentInline]
            elif obj.role == 'Counselor':
                return [CounselorInline]
        return []

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.profile_picture.url)
        return "No picture"
    profile_picture_preview.short_description = 'Profile Picture'

    @admin.action(description='Approve selected users')
    def approve_users(self, request, queryset):
        queryset.update(approval_status='approved', is_active=True)

    @admin.action(description='Reject selected users')
    def reject_users(self, request, queryset):
        queryset.update(approval_status='rejected', is_active=False)

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'year', 'contact_number')
    list_filter = ('year', 'course')
    search_fields = ('user__username', 'user__email', 'course')
    raw_id_fields = ('user',)

@admin.register(Counselor)
class CounselorAdmin(admin.ModelAdmin):
    list_display = ('user', 'email')
    search_fields = ('user__username', 'user__email', 'email')
    raw_id_fields = ('user',)

@admin.register(GuidanceSession)
class GuidanceSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'counselor', 'session_type', 'date', 'time_started', 'time_ended')
    list_filter = ('session_type', 'date', 'counselor')
    search_fields = ('student__user__username', 'counselor__user__username', 'problem_statement')
    date_hierarchy = 'date'
    raw_id_fields = ('student', 'counselor')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'counselor', 'date', 'time', 'status', 'created_at')
    list_filter = ('status', 'date', 'created_at')
    search_fields = ('student__user__username', 'counselor__user__username', 'purpose')
    date_hierarchy = 'date'
    raw_id_fields = ('student', 'counselor')
    actions = ['approve_appointments', 'decline_appointments']

    @admin.action(description='Approve selected appointments')
    def approve_appointments(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Decline selected appointments')
    def decline_appointments(self, request, queryset):
        queryset.update(status='declined')

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('session', 'followup_date', 'completed')
    list_filter = ('completed', 'followup_date')
    search_fields = ('session__student__user__username', 'followup_notes')
    date_hierarchy = 'followup_date'
    raw_id_fields = ('session',)