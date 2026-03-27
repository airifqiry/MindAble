from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
import logging
import re

from .models import Job, UserJobInteraction
from .serializers import JobListSerializer, JobDetailSerializer
from users.models import WorkplaceProfile
from mindable.mindable_app.job_fetcher import fetch_and_save_jobs

logger = logging.getLogger(__name__)


def _extract_skills(user_skills_raw: str) -> list[str]:
    # Supports both comma-separated skills and free-text profile summaries.
    if not user_skills_raw:
        return []

    chunks = [s.strip() for s in re.split(r"[,;\n]+", str(user_skills_raw)) if s.strip()]
    if len(chunks) > 1:
        return chunks

    text = chunks[0].lower() if chunks else ""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-\+#]{1,}", text)
    stopwords = {
        "and", "the", "that", "this", "with", "from", "have", "know", "into",
        "highly", "really", "very", "area", "areas", "about", "behind", "making",
        "im", "i", "m", "am", "in", "of", "to", "for", "on", "is", "are",
        "patient", "hardworking",
    }
    keywords: list[str] = []
    seen: set[str] = set()
    for w in words:
        if len(w) < 3 or w in stopwords:
            continue
        if w not in seen:
            seen.add(w)
            keywords.append(w)

    # Add high-signal multi-word terms when present.
    if "machine" in seen and "learning" in seen:
        keywords.insert(0, "machine learning")
    if "artificial" in seen and "intelligence" in seen:
        keywords.insert(0, "artificial intelligence")
    if "ai" in seen:
        keywords.insert(0, "ai")

    return keywords[:10]


class JobDiscoveryHubView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobListSerializer

    def get_queryset(self):
        user = self.request.user

        print("DEBUG: get_queryset called for user:", user)

        try:
            passport = WorkplaceProfile.objects.get(user=user)
            user_skills_raw = passport.skills
        except WorkplaceProfile.DoesNotExist:
            print("DEBUG: No WorkplaceProfile found for user", user)
            return Job.objects.none()

        print("DEBUG skills raw:", user_skills_raw)

        if not user_skills_raw:
            print("DEBUG: skills field is empty")
            return Job.objects.none()

        skills = _extract_skills(user_skills_raw)
        print("DEBUG skills list:", skills)
        print("DEBUG total jobs in DB:", Job.objects.count())
        print("DEBUG translated jobs:", Job.objects.filter(is_translated=True).count())

        
        skill_filter = Q()
        for skill in skills:
            skill_filter |= Q(title__icontains=skill)
            skill_filter |= Q(original_description__icontains=skill)

        user_has_matching_jobs = Job.objects.filter(
            skill_filter,
            is_translated=True
        ).exists()

        if not user_has_matching_jobs:
            try:
                fetch_and_save_jobs(
                    skills=skills,
                    include_remote=True,
                    include_onsite=True,
                )
            except Exception as e:
                logger.error("fetch_and_save_jobs failed: %s", e)
                print("DEBUG fetch error:", e)
                return Job.objects.none()

        dismissed_job_ids = UserJobInteraction.objects.filter(
            user=user,
            status='not_interested'
        ).values_list('job_id', flat=True)

        qs = Job.objects.filter(is_translated=True).exclude(id__in=dismissed_job_ids)

        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)

        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)

        
        if skills:
            skill_filter = Q()
            for skill in skills:
                skill_filter |= Q(title__icontains=skill)
                skill_filter |= Q(original_description__icontains=skill)
            qs = qs.filter(skill_filter)

        print("DEBUG: final qs count:", qs.count())
        return qs.order_by('-created_at')


class JobDetailView(generics.RetrieveAPIView):
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


class NotInterestedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        interaction, created = UserJobInteraction.objects.get_or_create(
            user=request.user,
            job=job,
            defaults={'status': 'not_interested'}
        )
        if not created and interaction.status != 'not_interested':
            interaction.status = 'not_interested'
            interaction.save()
        return Response(
            {"detail": "Job dismissed. We won't show you similar listings."},
            status=status.HTTP_200_OK
        )