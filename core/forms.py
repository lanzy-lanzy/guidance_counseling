from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from .models import User, Student, Counselor, Appointment, Interview
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border-gray-300'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border-gray-300'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'profile_picture']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md'})
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


class AppointmentForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input mt-1 block w-full rounded-md border-gray-300'})
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input mt-1 block w-full rounded-md border-gray-300'})
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea mt-1 block w-full rounded-md border-gray-300'})
    )

    class Meta:
        model = Appointment
        fields = ['counselor', 'date', 'time', 'purpose']
        widgets = {
            'counselor': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border-gray-300'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['counselor'].queryset = Counselor.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        counselor = cleaned_data.get('counselor')

        if not date or not time or not counselor:
            return cleaned_data

        # Check if date is not in the past
        from django.utils import timezone
        current_date = timezone.now().date()
        if date < current_date:
            raise forms.ValidationError("Cannot schedule appointments in the past.")

        # Check if time is within business hours (8 AM to 5 PM)
        from datetime import time as dt_time
        if time < dt_time(8, 0) or time > dt_time(17, 0):
            raise forms.ValidationError("Appointments must be scheduled between 8:00 AM and 5:00 PM.")

        # Check for double booking
        from django.db.models import Q
        existing_appointment = Appointment.objects.filter(
            counselor=counselor,
            date=date,
            time=time,
            status__in=['pending', 'approved']
        ).exists()

        if existing_appointment:
            raise forms.ValidationError("This time slot is already booked. Please select a different time.")

        return cleaned_data


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md'
                })


class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = [
            'address', 'contact_number', 'birth_date', 'birth_place', 'age',
            'civil_status', 'religion', 'father_name', 'father_occupation',
            'father_education', 'mother_name', 'mother_occupation',
            'mother_education', 'parents_marital_status', 'elementary_school',
            'elementary_year_graduated', 'high_school', 'high_school_year_graduated',
            'college_school', 'college_course', 'reason_for_interview',
            'presenting_problem', 'background_of_problem', 'counselor_notes',
            'recommendations', 'follow_up_needed'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_place': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'civil_status': forms.Select(attrs={'class': 'form-control'}),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'father_occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'father_education': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_education': forms.TextInput(attrs={'class': 'form-control'}),
            'parents_marital_status': forms.Select(attrs={'class': 'form-control'}),
            'elementary_school': forms.TextInput(attrs={'class': 'form-control'}),
            'elementary_year_graduated': forms.TextInput(attrs={'class': 'form-control'}),
            'high_school': forms.TextInput(attrs={'class': 'form-control'}),
            'high_school_year_graduated': forms.TextInput(attrs={'class': 'form-control'}),
            'college_school': forms.TextInput(attrs={'class': 'form-control'}),
            'college_course': forms.TextInput(attrs={'class': 'form-control'}),
            'reason_for_interview': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'presenting_problem': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'background_of_problem': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'counselor_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'follow_up_needed': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
