from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Job, UserJobInteraction
from .serializers import JobListSerializer, JobDetailSerializer
from users.models import WorkplaceProfile
from mindable.mindable_app.job_fetcher import fetch_and_save_jobs


class JobDiscoveryHubView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobListSerializer

    def get_queryset(self):
        user = self.request.user

        try:
            passport = WorkplaceProfile.objects.get(user=user)
            user_skills_raw = passport.skills
        except WorkplaceProfile.DoesNotExist:
            return Job.objects.none()

        if not user_skills_raw:
            return Job.objects.none()

        skills = [s.strip() for s in user_skills_raw.split(',') if s.strip()]

        if not Job.objects.exists():
            try:
                fetch_and_save_jobs(
                    skills=skills,
                    include_remote=True,
                    include_onsite=True,
                )
                Job.objects.update(is_translated=True)
            except Exception:
                pass

        dismissed_job_ids = UserJobInteraction.objects.filter(
            user=user,
            status='not_interested'
        ).values_list('job_id', flat=True)

        qs = Job.objects.filter(
            is_translated=True
        ).exclude(
            id__in=dismissed_job_ids
        )

        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)

        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)

        if skills:
            from django.db.models import Q
            skill_filter = Q()
            for skill in skills:
                skill_filter |= Q(required_skills__icontains=skill)
            qs = qs.filter(skill_filter)

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