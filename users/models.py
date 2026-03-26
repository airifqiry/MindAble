from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

class User(AbstractUser):
    is_job_seeker = models.BooleanField(default=True)
    is_employer = models.BooleanField(default=False)
    daily_capacity = models.IntegerField(
        default=100, 
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

class WorkplacePassport(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='passport')
    resume_pdf = models.FileField(upload_to='resumes/', null=True, blank=True)
    experience_summary = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    success_enablers = models.JSONField(default=dict, blank=True)
    dealbreakers = models.JSONField(default=list, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Passport: {self.user.username}"