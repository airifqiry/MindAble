from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField


class Company(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_verified_inclusive = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('full-time', 'Full-Time'),
        ('part-time', 'Part-Time'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    external_url = models.URLField()

    original_description = models.TextField()
    translated_title = models.CharField(max_length=255, blank=True)
    translated_tasks = models.JSONField(default=list, blank=True)

    toxicity_warnings = models.JSONField(default=list, blank=True)
 

    required_skills = models.JSONField(default=list, blank=True)

    skills_embedding = ArrayField(models.FloatField(), size=384, null=True, blank=True)
    needs_embedding = ArrayField(models.FloatField(), size=384, null=True, blank=True)
    is_translated = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.translated_title or self.title} at {self.company.name}"


class UserJobInteraction(models.Model):
    STATUS_CHOICES = [
        ('not_interested', 'Not Interested'),
        ('saved', 'Saved'),
        ('applied', 'Applied'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_interactions'
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')

    def __str__(self):
        return f"{self.user} — {self.job.title} — {self.status}"