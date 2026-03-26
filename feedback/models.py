from django.db import models
from django.conf import settings

class JobFeedback(models.Model):

    STATUS_CHOICES = [
        ('saved',        'Saved'),
        ('applied',      'Applied'),
        ('not_interested', 'Not Interested'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    note = models.TextField(blank=True)       # optional personal note
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'job')     # one feedback per user per job

    def str(self):
        return f"{self.user} → {self.job} [{self.status}]"