from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from users.models import WorkplaceProfile

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password'
    }))


class RegisterForm(forms.ModelForm):
    """
    Do not put `password` in Meta.fields — User.password is the hashed field and breaks validation.
    Use plain CharFields + set_password in save().
    """

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            self.add_error("confirm_password", "Passwords do not match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class PassportStep1Form(forms.ModelForm):
    class Meta:
        model = WorkplaceProfile
        fields = ['skills', 'experience_summary']
        widgets = {
            'skills': forms.Textarea(attrs={'placeholder': 'What are you great at?'}),
            'experience_summary': forms.Textarea(attrs={'placeholder': 'Tell us about your background.'}),
        }


class PassportStep2Form(forms.ModelForm):
    class Meta:
        model = WorkplaceProfile
        fields = ['mental_disability']
        widgets = {
            'mental_disability': forms.Textarea(attrs={'placeholder': 'Describe your neurotype or condition in your own words.'}),
        }


class PassportStep3Form(forms.ModelForm):
    class Meta:
        model = WorkplaceProfile
        fields = ['dealbreakers']


class PassportStep4Form(forms.ModelForm):
    class Meta:
        model = WorkplaceProfile
        fields = ['success_enablers']