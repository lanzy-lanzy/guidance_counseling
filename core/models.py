from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('Counselor', 'Counselor'),
        ('Student', 'Student'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending'
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        related_name='custom_user_set',
        related_query_name='custom_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        related_name='custom_user_set',
        related_query_name='custom_user'
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.is_active = True
            self.approval_status = 'approved'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    course = models.CharField(max_length=100)
    year = models.IntegerField()
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    reason_for_referral = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.course}, Year {self.year})"

class Counselor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='counselor_profile')
    email = models.EmailField()

    def __str__(self):
        return self.user.username

class GuidanceSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('Interview', 'Interview'),
        ('Referral', 'Referral'),
        ('Assessment', 'Assessment'),
        ('Follow-Up', 'Follow-Up'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="sessions")
    counselor = models.ForeignKey(Counselor, on_delete=models.CASCADE, related_name="sessions")
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    date = models.DateField(auto_now_add=True)
    time_started = models.DateTimeField(blank=True, null=True)
    time_ended = models.DateTimeField(blank=True, null=True)
    problem_statement = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    action_items = models.TextField(blank=True, null=True)
    next_steps = models.TextField(blank=True, null=True)
    appointment = models.OneToOneField('Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='session')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def start_session(self):
        if self.status == 'scheduled':
            self.status = 'in_progress'
            self.time_started = timezone.now()
            self.save()

    def end_session(self, problem_statement=None, recommendations=None, notes=None, action_items=None, next_steps=None):
        if self.status == 'in_progress':
            self.status = 'completed'
            self.time_ended = timezone.now()
            if problem_statement:
                self.problem_statement = problem_statement
            if recommendations:
                self.recommendations = recommendations
            if notes:
                self.notes = notes
            if action_items:
                self.action_items = action_items
            if next_steps:
                self.next_steps = next_steps
            self.save()

    def cancel_session(self):
        self.status = 'cancelled'
        self.save()

    @property
    def duration(self):
        if self.time_started and self.time_ended:
            return self.time_ended - self.time_started
        return None

    def __str__(self):
        return f"{self.session_type} with {self.student.user.username} by {self.counselor.user.username}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="appointments")
    counselor = models.ForeignKey(Counselor, on_delete=models.CASCADE, related_name="appointments")
    date = models.DateField()
    time = models.TimeField()
    purpose = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment for {self.student.user.username} with {self.counselor.user.username}"

class FollowUp(models.Model):
    session = models.OneToOneField(GuidanceSession, on_delete=models.CASCADE, related_name="followup")
    followup_date = models.DateField()
    followup_notes = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"Follow-Up for {self.session.student.user.username} ({status})"

class Interview(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='interview_forms')
    counselor = models.ForeignKey(Counselor, on_delete=models.CASCADE, related_name='conducted_interviews')
    date = models.DateField(auto_now_add=True)
    
    # Personal Information
    address = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    birth_date = models.DateField()
    birth_place = models.CharField(max_length=255)
    age = models.IntegerField()
    civil_status = models.CharField(max_length=50)
    religion = models.CharField(max_length=100)
    
    # Family Background
    father_name = models.CharField(max_length=255, blank=True, null=True)
    father_occupation = models.CharField(max_length=255, blank=True, null=True)
    father_education = models.CharField(max_length=255, blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)
    mother_occupation = models.CharField(max_length=255, blank=True, null=True)
    mother_education = models.CharField(max_length=255, blank=True, null=True)
    parents_marital_status = models.CharField(max_length=100)
    
    # Educational Background
    elementary_school = models.CharField(max_length=255)
    elementary_year_graduated = models.CharField(max_length=50)
    high_school = models.CharField(max_length=255)
    high_school_year_graduated = models.CharField(max_length=50)
    college_school = models.CharField(max_length=255, blank=True, null=True)
    college_course = models.CharField(max_length=255, blank=True, null=True)
    
    # Interview Details
    reason_for_interview = models.TextField()
    presenting_problem = models.TextField()
    background_of_problem = models.TextField()
    counselor_notes = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    follow_up_needed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Interview Form - {self.student.user.username} - {self.date}"
