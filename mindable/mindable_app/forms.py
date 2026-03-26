from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, WorkplacePassport  # fix import to use your custom User

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class LoginForm(AuthenticationForm):
    pass

class ProfileStep1Form(forms.Form):
    """Skills & Experience"""
    skills = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'e.g. I am good at focused research, writing clearly, working independently...'}),
        label="What are you good at?"
    )
    experience_summary = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'e.g. I have 2 years experience in data entry and customer support...'}),
        label="Briefly describe your work experience (gaps are completely fine)",
        required=False
    )

class ProfileStep2Form(forms.Form):
    """Neurotype"""
    neurotype = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g. ADHD, Autism, Anxiety, Depression...'}),
        label="What condition(s) do you manage? (this stays private and helps us filter jobs for you)",
        required=False
    )

class ProfileStep3Form(forms.Form):
    """Disadvantages / challenges"""
    disadvantages = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'e.g. I struggle with phone calls, open offices, strict deadlines...'}),
        label="What situations or tasks are harder for you?"
    )

class ProfileStep4Form(forms.Form):
    """Success Enablers / accommodations"""
    success_enablers = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'e.g. Written instructions, noise-cancelling headphones, flexible hours, remote work...'}),
        label="What do you need in place to do your best work?"
    )
    resume_pdf = forms.FileField(
        required=False,
        label="Upload your CV (optional)"
    )