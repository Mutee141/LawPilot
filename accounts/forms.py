from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from cases.models import Case, Task

class LawyerSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone_number", "role")
        help_texts = {
            'role': 'Select your role. You can manage this in firm settings later.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make role field more user-friendly
        self.fields['role'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        # Role is selected by user during signup
        if commit:
            user.save()
        return user


class TaskAssignmentForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'case', 'assigned_to', 'priority', 'deadline']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'case': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter cases by user's firm
        if user.firm:
            self.fields['case'].queryset = Case.objects.filter(firm=user.firm)
            # Only show junior lawyers from the same firm as assignment options
            self.fields['assigned_to'].queryset = User.objects.filter(
                firm=user.firm,
                role='junior_lawyer'
            )
        else:
            self.fields['case'].queryset = Case.objects.none()
            self.fields['assigned_to'].queryset = User.objects.none()
