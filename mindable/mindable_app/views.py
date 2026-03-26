from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm, PassportStep1Form, PassportStep2Form, PassportStep3Form, PassportStep4Form
from .models import WorkplacePassport


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('basecamp')
    else:
        form = RegisterForm()
    return render(request, 'auth.html', {
        'register_form': form,
        'login_form': LoginForm(),
        'active_tab': 'register'   # tells the JS to show the signup tab
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
    return render(request, 'auth.html', {
        'login_form': form,
        'register_form': RegisterForm(),
        'active_tab': 'login'   # tells the JS to show the login tab
    })

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def passport_step4(request):
    if hasattr(request.user, 'passport'):
        return redirect('basecamp')
    if 'passport_step3' not in request.session:
        return redirect('passport_step1')

    if request.method == 'POST':
        form = PassportStep4Form(request.POST, request.FILES)
        if form.is_valid():
            # Collect all session data
            step1 = request.session.get('passport_step1', {})
            step2 = request.session.get('passport_step2', {})
            step3 = request.session.get('passport_step3', {})

            # Build the passport object and save to DB
            passport = WorkplacePassport(
                user=request.user,
                skills=step1.get('skills', ''),
                experience_summary=step1.get('experience_summary', ''),
                success_enablers={
                    'neurotype': step2.get('neurotype', ''),
                    'enablers': form.cleaned_data['success_enablers'],
                },
                dealbreakers=step3.get('disadvantages', '').split(','),
            )
            if form.cleaned_data.get('resume_pdf'):
                passport.resume_pdf = form.cleaned_data['resume_pdf']

            passport.save()

            # Clean up session
            for key in ['passport_step1', 'passport_step2', 'passport_step3']:
                request.session.pop(key, None)

            return redirect('basecamp')
    else:
        form = PassportStep4Form()

    return render(request, 'passport/step4.html', {'form': form, 'step': 4})