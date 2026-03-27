from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import (
    RegisterForm, 
    LoginForm, 
    PassportStep1Form, 
    PassportStep2Form, 
    PassportStep3Form, 
    PassportStep4Form
)
from users.models import WorkplaceProfile



def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('passport_step1')
    else:
        form = RegisterForm()
    return render(request, 'signup.html', {
        'register_form': form,
        'login_form': LoginForm(),
        'active_tab': 'register'
    })

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('basecamp')
    else:
        form = LoginForm()
    return render(request, 'signup.html', {
        'login_form': form,
        'register_form': RegisterForm(),
        'active_tab': 'login'
    })

def logout_view(request):
    logout(request)
    return redirect('login')



@login_required
def passport_step1(request):
    if request.method == 'POST':
        form = PassportStep1Form(request.POST)
        if form.is_valid():
            request.session['passport_step1'] = form.cleaned_data
            return redirect('passport_step2')
    else:
        form = PassportStep1Form()
    return render(request, 'profile/step1.html', {'form': form, 'step': 1})

@login_required
def passport_step2(request):
    if 'passport_step1' not in request.session:
        return redirect('passport_step1')
    
    if request.method == 'POST':
        form = PassportStep2Form(request.POST)
        if form.is_valid():
            request.session['passport_step2'] = form.cleaned_data
            return redirect('passport_step3')
    else:
        form = PassportStep2Form()
    return render(request, 'profile/step2.html', {'form': form, 'step': 2})

@login_required
def passport_step3(request):
    if 'passport_step2' not in request.session:
        return redirect('passport_step2')

    if request.method == 'POST':
        form = PassportStep3Form(request.POST)
        if form.is_valid():
            request.session['passport_step3'] = form.cleaned_data
            return redirect('passport_step4')
    else:
        form = PassportStep3Form()
    return render(request, 'profile/step3.html', {'form': form, 'step': 3})

@login_required
def passport_step4(request):
    if 'passport_step3' not in request.session:
        return redirect('passport_step3')

    if request.method == 'POST':
        form = PassportStep4Form(request.POST, request.FILES)
        if form.is_valid():
            # Retrieve all data from session
            s1 = request.session.get('passport_step1', {})
            s2 = request.session.get('passport_step2', {})
            s3 = request.session.get('passport_step3', {})
            
            # Save to the Database (WorkplaceProfile)
            profile = WorkplaceProfile.objects.create(
                user=request.user,
                skills=s1.get('skills', ''),
                experience_summary=s1.get('experience_summary', ''),
                mental_disability=s2.get('mental_disability', ''),
                dealbreakers=s3.get('dealbreakers', []),
                success_enablers=form.cleaned_data.get('success_enablers', {})
            )
            
            # Clean up session
            for key in ['passport_step1', 'passport_step2', 'passport_step3']:
                request.session.pop(key, None)
                
            return redirect('basecamp')
    else:
        form = PassportStep4Form()
    return render(request, 'profile/step4.html', {'form': form, 'step': 4})

@login_required
def basecamp(request):
    # This is your main dashboard after login/profile setup
    return render(request, 'basecamp.html')