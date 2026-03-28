from rest_framework import serializers
from .logistics import logistics_highlights_for_job
from .models import Job


class JobListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for the job feed cards.
    Shows just enough for the user to decide whether to click in.
    """

    company = serializers.CharField(source='company.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    display_title = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    match_explanation = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    company_label = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    match_reason = serializers.SerializerMethodField()
    link = serializers.CharField(source="external_url", read_only=True)
    matched_skills = serializers.SerializerMethodField()
    matched_strengths = serializers.SerializerMethodField()
    detected_conflicts = serializers.SerializerMethodField()
    penalties_applied = serializers.SerializerMethodField()
    final_reason = serializers.SerializerMethodField()
    dedupe_key = serializers.SerializerMethodField()
    matched_technical_skills = serializers.SerializerMethodField()
    matched_general_skills = serializers.SerializerMethodField()
    match_tier = serializers.SerializerMethodField()
    matching_mode = serializers.SerializerMethodField()
    match_quality = serializers.SerializerMethodField()
    fallback_used = serializers.SerializerMethodField()
    penalty_total = serializers.SerializerMethodField()

    def get_display_title(self, obj):
        return obj.translated_title or obj.title

    def get_match_score(self, obj):
        score = getattr(obj, "_match_score", None)
        if score is None:
            return None
        return round(float(score), 4)

    def get_match_explanation(self, obj):
        return getattr(obj, "_final_reason", None) or getattr(obj, "_match_explanation", "") or ""

    def get_title(self, obj):
        return obj.translated_title or obj.title

    def get_company_label(self, obj):
        return obj.company.name if obj.company_id else ""

    def get_description(self, obj):
        text = (obj.original_description or "").strip()
        return text[:500] + ("..." if len(text) > 500 else "")

    def get_score(self, obj):
        return self.get_match_score(obj)

    def get_match_reason(self, obj):
        return self.get_match_explanation(obj)

    def get_matched_skills(self, obj):
        return getattr(obj, "_matched_skills", []) or []

    def get_matched_strengths(self, obj):
        return getattr(obj, "_matched_strengths", []) or []

    def get_detected_conflicts(self, obj):
        return getattr(obj, "_detected_conflicts", []) or []

    def get_penalties_applied(self, obj):
        return getattr(obj, "_penalties_applied", []) or []

    def get_final_reason(self, obj):
        return getattr(obj, "_final_reason", "") or self.get_match_explanation(obj)

    def get_dedupe_key(self, obj):
        return getattr(obj, "_dedupe_key", "") or ""

    def get_matched_technical_skills(self, obj):
        return getattr(obj, "_matched_technical_skills", []) or []

    def get_matched_general_skills(self, obj):
        return getattr(obj, "_matched_general_skills", []) or []

    def get_match_tier(self, obj):
        return getattr(obj, "_match_tier", "") or ""

    def get_matching_mode(self, obj):
        return getattr(obj, "_matching_mode", "") or ""

    def get_match_quality(self, obj):
        return getattr(obj, "_match_quality", "") or ""

    def get_fallback_used(self, obj):
        return bool(getattr(obj, "_fallback_used", False))

    def get_penalty_total(self, obj):
        v = getattr(obj, "_penalty_total", None)
        return v if v is not None else None

    class Meta:
        model = Job
        fields = [
            'id',
            'display_title',
            'translated_title',
            'company',
            'company_name',
            'location',
            'job_type',
            'toxicity_warnings',
            'match_score',
            'match_explanation',
            'title',
            'company_label',
            'description',
            'score',
            'match_reason',
            'link',
            'matched_skills',
            'matched_strengths',
            'detected_conflicts',
            'penalties_applied',
            'final_reason',
            'dedupe_key',
            'matched_technical_skills',
            'matched_general_skills',
            'match_tier',
            'matching_mode',
            'match_quality',
            'fallback_used',
            'penalty_total',
            'created_at',
        ]


class JobDetailSerializer(serializers.ModelSerializer):

    company_name = serializers.CharField(source='company.name', read_only=True)
    display_title = serializers.SerializerMethodField()
    accessible_summary = serializers.SerializerMethodField()
    work_logistics = serializers.SerializerMethodField()

    def get_display_title(self, obj):
        return obj.translated_title or obj.title

    def get_accessible_summary(self, obj):
        text = getattr(obj, "_accessible_summary", None)
        if text:
            return text
        tasks = obj.translated_tasks or []
        if not tasks:
            return ""
        return " ".join(str(t).strip() for t in tasks if t)

    def get_work_logistics(self, obj):
        return logistics_highlights_for_job(obj)

    class Meta:
        model = Job
        fields = [
            'id',
            'display_title',
            'translated_title',
            'company',
            'company_name',
            'location',
            'job_type',
            'external_url',
            'accessible_summary',
            'work_logistics',
            'translated_tasks',
            'toxicity_warnings',
            'required_skills',
            'created_at',
        ]