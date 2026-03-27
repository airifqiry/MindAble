from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import User, WorkplaceProfile
from .forms import (
    RegisterForm,
    LoginForm,
    PassportStep1Form,
    PassportStep2Form,
    PassportStep3Form,
    PassportStep4Form,
)

from mindable.mindable_app.profile_analyzer import analyze_profile
from mindable.mindable_app.embedding_service import build_user_embeddings


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
    return render(request, 'mindable/signup.html', {
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
    return render(request, 'mindable/signup.html', {
        'login_form': form,
        'register_form': RegisterForm(),
        'active_tab': 'login'
    })


def logout_view(request):
    logout(request)
    return redirect('login')


# --- Workplace Profile (Passport) Multi-Step Views ---

@login_required
def passport_step1(request):
    if request.method == 'POST':
        form = PassportStep1Form(request.POST)
        if form.is_valid():
            request.session['passport_step1'] = form.cleaned_data
            return redirect('passport_step2')
    else:
        form = PassportStep1Form()
    return render(request, 'mindable/onboarding.html', {'form': form, 'step': 1})


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
    return render(request, 'mindable/onboarding.html', {'form': form, 'step': 2})


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
    return render(request, 'mindable/onboarding.html', {'form': form, 'step': 3})


@login_required
def passport_step4(request):
    if 'passport_step3' not in request.session:
        return redirect('passport_step3')

    if request.method == 'POST':
        form = PassportStep4Form(request.POST, request.FILES)
        if form.is_valid():
            s1 = request.session.get('passport_step1', {})
            s2 = request.session.get('passport_step2', {})
            s3 = request.session.get('passport_step3', {})

            # Combine all steps into one text block for Aiya's analyzer.
            profile_text = "\n".join(filter(None, [
                s1.get('skills', ''),
                s1.get('experience_summary', ''),
                s2.get('mental_disability', ''),
                " ".join(s3.get('dealbreakers', [])),
                str(form.cleaned_data.get('success_enablers', '')),
            ]))

            # Step 1 — Aiya: extract structured JSON from the profile text.
            try:
                profile_json = analyze_profile(profile_text)
            except (RuntimeError, ValueError):
                profile_json = {}

            # Step 2 — Ani: generate embeddings from the profile JSON.
            # Falls back to None if profile is missing required fields.
            try:
                skills_embedding, needs_embedding = build_user_embeddings(profile_json)
            except (ValueError, Exception):
                skills_embedding = None
                needs_embedding = None

            # Step 3 — Save everything to WorkplaceProfile in one go.
            WorkplaceProfile.objects.create(
                user=request.user,
                skills=s1.get('skills', ''),
                experience_summary=s1.get('experience_summary', ''),
                mental_disability=s2.get('mental_disability', ''),
                dealbreakers=s3.get('dealbreakers', []),
                success_enablers=form.cleaned_data.get('success_enablers', {}),
                skills_embedding=skills_embedding,
                needs_embedding=needs_embedding,
            )

            # Clean up session data.
            for key in ['passport_step1', 'passport_step2', 'passport_step3']:
                request.session.pop(key, None)

            return redirect('basecamp')
    else:
        form = PassportStep4Form()
    return render(request, 'mindable/onboarding.html', {'form': form, 'step': 4})


@login_required
def basecamp(request):
    return render(request, 'mindable/dashboard.html')