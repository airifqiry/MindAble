from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('seeker', 'Job Seeker'),
        ('employer', 'Employer'),
    ]
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seeker')
    phone         = models.CharField(max_length=20, blank=True)
    remote_only   = models.BooleanField(default=False)
    flex_schedule = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class WorkplacePassport(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user                = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='passport')
    disability_type     = models.CharField(max_length=100, blank=True)
    success_enablers    = models.TextField(blank=True)
    accommodation_needs = models.TextField(blank=True)
    share_with_employer = models.BooleanField(default=False)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Passport: {self.user.email}"
