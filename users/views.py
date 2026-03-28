import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .models import WorkplaceProfile, ChatMessage
from .forms import RegisterForm, LoginForm


def register_view(request):
    if request.method == 'POST':
        post = request.POST.copy()

        email = (post.get("email") or "").strip()
        if email and not (post.get("username") or "").strip():
            post["username"] = email
        form = RegisterForm(post)
        if form.is_valid():
            user = form.save()
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
def chat(request):
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
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)

    skills        = (payload.get('skills')        or '').strip()
    values        = (payload.get('values')        or '').strip()
    neurotype     = (payload.get('neurotype')     or '').strip()
    disadvantages = (payload.get('disadvantages') or '').strip()
    enablers      = (payload.get('enablers')      or '').strip()

    if not skills:
        return JsonResponse({'detail': 'Skills is required.'}, status=400)

    experience_summary = "\n\n".join([p for p in [values, disadvantages] if p])

    profile, created = WorkplaceProfile.objects.get_or_create(user=request.user)
    profile.skills             = skills
    profile.experience_summary = experience_summary
    profile.mental_disability  = neurotype
    profile.success_enablers   = {'text': enablers} if enablers else {}

    profile_text = " ".join(filter(None, [skills, values, neurotype, disadvantages, enablers]))

    try:
        from mindable.mindable_app.profile_analyzer import analyze_profile
        from mindable.mindable_app.embedding_service import build_user_embeddings, get_embedding_version

        analyzed = analyze_profile(profile_text)
        skills_emb, needs_emb = build_user_embeddings(analyzed)
        profile.skills_embedding = skills_emb
        profile.needs_embedding = needs_emb
        profile.embedding_version = get_embedding_version()
  
        profile.success_enablers = {
            'text': enablers,
            'analyzed_profile': analyzed,
        }
        profile.dealbreakers = analyzed.get('limitations') or []
    except Exception as e:
        return JsonResponse(
            {'detail': f'AI analysis/embedding failed: {str(e)}'},
            status=500
        )

    profile.save(update_fields=[
        'skills',
        'experience_summary',
        'mental_disability',
        'success_enablers',
        'dealbreakers',
        'skills_embedding',
        'needs_embedding',
        'embedding_version',
        'last_updated',
    ])

    return JsonResponse({'detail': 'Saved.', 'redirect_url': '/jobs/'}, status=200)


@login_required
@require_POST
def chat_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    user_message = str(payload.get("message") or "").strip()
    topic = str(payload.get("topic") or "about-yourself").strip()
    job_id = payload.get("job_id")
    try:
        job_id = int(job_id) if job_id is not None else None
    except (TypeError, ValueError):
        job_id = None

    if not user_message:
        return JsonResponse({"detail": "message is required."}, status=400)

    try:
        ChatMessage.objects.create(
            user=request.user,
            role="user",
            content=user_message,
        )
        history_rows = ChatMessage.objects.filter(user=request.user).order_by("timestamp", "id")
        history = [{"role": row.role, "content": row.content} for row in history_rows]

        from mindable.mindable_app.interview_chatbot import run_interview_turn

        out = run_interview_turn(
            user=request.user,
            topic=topic,
            history=history,
            job_id=job_id,
        )

        turn = out.get("turn", {}) if isinstance(out, dict) else {}
        assistant_text = str(turn.get("assistant_message") or "").strip()
        if turn.get("feedback_good"):
            assistant_text += f"\nWhat went well: {turn['feedback_good']}"
        if turn.get("feedback_improve"):
            assistant_text += f"\nWhat to improve: {turn['feedback_improve']}"
        if turn.get("feedback_how"):
            assistant_text += f"\nHow to improve: {turn['feedback_how']}"
        if turn.get("next_question"):
            assistant_text += f"\nNext question: {turn['next_question']}"

        assistant_text = assistant_text.strip()
        if not assistant_text:
            return JsonResponse({"detail": "Claude returned an empty response."}, status=502)

        ChatMessage.objects.create(
            user=request.user,
            role="assistant",
            content=assistant_text,
        )
        out["assistant_message"] = assistant_text
    except Exception as exc:
        return JsonResponse({"detail": f"Interview coach failed: {str(exc)}"}, status=500)

    return JsonResponse(out, status=200)


@login_required
def chat_history(request):
    rows = ChatMessage.objects.filter(user=request.user).order_by("timestamp", "id")
    data = [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "timestamp": row.timestamp.isoformat(),
        }
        for row in rows
    ]
    return JsonResponse(data, safe=False, status=200)


@login_required
@require_POST
def prep_chat_api(request):
    return chat_api(request)