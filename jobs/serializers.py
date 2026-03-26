from rest_framework import serializers
from .models import Job


class JobListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for the job feed cards.
    Shows just enough for the user to decide whether to click in.
    """

    class Meta:
        model = Job
        fields = [
            'id',
            'translated_title',
            'company',
            'location',
            'job_type',
            'toxicity_warnings',
            'created_at',
        ]


class JobDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for the Job Detail / AI Translator page.

    translated_tasks  → plain-language bullet list
        e.g. ["Write weekly email updates", "Attend 1 meeting per week"]

    toxicity_warnings → warning label strings
        e.g. ["Original post mentioned: 'must work under extreme pressure'"]

    original_description is intentionally excluded —
    users only ever see the AI-translated version.
    """

    class Meta:
        model = Job
        fields = [
            'id',
            'translated_title',
            'company',
            'location',
            'job_type',
            'external_url',
            'translated_tasks',
            'toxicity_warnings',
            'required_skills',
            'created_at',
        ]