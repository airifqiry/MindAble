from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.postgres.fields import ArrayField

class User(AbstractUser):
    is_job_seeker = models.BooleanField(default=True)
    is_employer = models.BooleanField(default=False)
    daily_capacity = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

class WorkplaceProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    resume_pdf = models.FileField(upload_to='resumes/', null=True, blank=True)
    experience_summary = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    success_enablers = models.JSONField(default=dict, blank=True)
    dealbreakers = models.JSONField(default=list, blank=True)
    mental_disability = models.TextField(blank=True)
    skills_embedding = ArrayField(models.FloatField(), size=384, null=True, blank=True)
    needs_embedding = ArrayField(models.FloatField(), size=384, null=True, blank=True)
    embedding_version = models.CharField(max_length=64, blank=True, default="")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"
    
class RejectedJob(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="rejected_jobs",
    )
    job_id = models.CharField(max_length=100)
    skills_embedding = ArrayField(models.FloatField(), size=384)
    needs_embedding = ArrayField(models.FloatField(), size=384)
    reason = models.TextField(null=True, blank=True)
    rejected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "job_id")


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp", "id"]