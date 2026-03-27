import json

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required

from .models import WorkplaceProfile
from .forms import RegisterForm, LoginForm


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('onboarding')
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


@login_required
def home(request):
    return render(request, 'mindable/dashboard.html')


@login_required
def jobs(request):
    return render(request, 'mindable/jobs.html')


@login_required
def prep(request):
    return render(request, 'mindable/prep.html')


@login_required
def onboarding(request):
    return render(request, 'mindable/onboarding.html')


@login_required
def basecamp(request):
    return render(request, 'mindable/dashboard.html')


@login_required
@require_POST
def profile_upsert_api(request):
    """
    Single-page onboarding: save/update WorkplaceProfile from JSON payload.
    """
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)

    skills = (payload.get('skills') or '').strip()
    values = (payload.get('values') or '').strip()
    neurotype = (payload.get('neurotype') or '').strip()
    disadvantages = (payload.get('disadvantages') or '').strip()
    enablers = (payload.get('enablers') or '').strip()

    if not skills:
        return JsonResponse({'detail': 'Skills is required.'}, status=400)

    experience_summary = "\n\n".join([part for part in [values, disadvantages] if part])

    profile, _created = WorkplaceProfile.objects.get_or_create(user=request.user)
    profile.skills = skills
    profile.experience_summary = experience_summary
    profile.mental_disability = neurotype
    profile.success_enablers = {'text': enablers} if enablers else {}
    profile.save(update_fields=[
        'skills',
        'experience_summary',
        'mental_disability',
        'success_enablers',
        'last_updated',
    ])

    return JsonResponse({'detail': 'Saved.', 'redirect_url': '/jobs/'}, status=200)


@login_required
def basecamp(request):
    return render(request, 'mindable/dashboard.html')