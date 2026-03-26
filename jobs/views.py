from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Job, UserJobInteraction
from .serializers import JobListSerializer, JobDetailSerializer
from users.models import WorkplaceProfile  # adjust app name if needed


# ─────────────────────────────────────────────
# 1. JOB DISCOVERY HUB  →  GET /api/jobs/
# ─────────────────────────────────────────────
class JobDiscoveryHubView(generics.ListAPIView):
    """
    Returns a paginated, passport-matched, translated job feed for the
    logged-in user.

    Matching logic:
      1. Exclude jobs the user has already dismissed ("not_interested").
      2. Only show jobs where AI translation is complete (is_translated=True).
      3. Filter by overlap between Job.required_skills and the
         user's WorkplaceProfile skills.

    Query params (all optional):
      ?page=1            pagination
      ?location=remote   filter by location keyword
      ?job_type=remote   filter by job type (full-time, part-time, remote, hybrid)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = JobListSerializer

    def get_queryset(self):
        user = self.request.user

        # --- fetch the user's passport ---
        try:
            passport = WorkplaceProfile.objects.get(user=user)
            user_skills = passport.skills  # e.g. ["Python", "data entry", "writing"]
        except WorkplaceProfile.DoesNotExist:
            # Passport not completed — return empty feed
            return Job.objects.none()

        # --- exclude dismissed jobs ---
        dismissed_job_ids = UserJobInteraction.objects.filter(
            user=user,
            status='not_interested'
        ).values_list('job_id', flat=True)

        # --- base queryset: translated only, not dismissed ---
        qs = Job.objects.filter(
            is_translated=True
        ).exclude(
            id__in=dismissed_job_ids
        )

        # --- optional query param filters ---
        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)

        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)

        # --- skill matching ---
        if user_skills:
            from django.db.models import Q
            skill_filter = Q()
            for skill in user_skills:
                skill_filter |= Q(required_skills__icontains=skill)
            qs = qs.filter(skill_filter)

        return qs.order_by('-created_at')


# ─────────────────────────────────────────────
# 2. JOB DETAIL / AI TRANSLATOR  →  GET /api/jobs/<id>/
# ─────────────────────────────────────────────
class JobDetailView(generics.RetrieveAPIView):
    """
    Returns the AI-translated version of a single job.

    Surfaces:
      - translated_title
      - translated_tasks  (plain-language bullets)
      - toxicity_warnings (stress/pressure flags)
      - external_url      ("Apply Externally" button destination)

    Never exposes original_description to the frontend.

    If is_translated=False (AI hasn't processed it yet),
    returns 202 Accepted so the frontend can show a loading state.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = JobDetailSerializer
    queryset = Job.objects.all()

    def retrieve(self, request, *args, **kwargs):
        job = self.get_object()

        if not job.is_translated:
            return Response(
                {"detail": "This job is still being processed. Please check back shortly."},
                status=status.HTTP_202_ACCEPTED
            )

        return super().retrieve(request, *args, **kwargs)


# ─────────────────────────────────────────────
# 3. NOT INTERESTED  →  POST /api/jobs/<id>/not-interested/
# ─────────────────────────────────────────────
class NotInterestedView(APIView):
    """
    Marks a job as 'not_interested' for the logged-in user.

    Effect:
      - Saves a UserJobInteraction(status='not_interested') to the DB.
      - This job will be excluded from the user's feed going forward.

    Similarity suppression note:
      The blueprint says the AI should suppress *similar* jobs too.
      This view records the signal — the AI/scraper team should read
      these interactions to update their similarity suppression model.

    Idempotent: calling this twice on the same job is safe.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk)

        interaction, created = UserJobInteraction.objects.get_or_create(
            user=request.user,
            job=job,
            defaults={'status': 'not_interested'}
        )

        if not created and interaction.status != 'not_interested':
            # Job was previously saved/applied — update to not_interested
            interaction.status = 'not_interested'
            interaction.save()

        return Response(
            {"detail": "Job dismissed. We won't show you similar listings."},
            status=status.HTTP_200_OK
        )