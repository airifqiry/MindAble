from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    The MindAble User Model. 
    Fixes the 'Reverse Accessor' clash by setting unique related_names.
    """
    is_employer = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set', 
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True
    )

class WorkplacePassport(models.Model):
    """
    The Core Product: Stores the neurodivergent user's boundaries.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='passport')
    
    # Capacity Check (The 'Spoon Slider')
    energy_level = models.IntegerField(default=5) 
    
    # Dealbreakers (Based on your strategy)
    avoid_loud_environments = models.BooleanField(default=False)
    avoid_cold_calling = models.BooleanField(default=False)
    avoid_unpredictable_shifts = models.BooleanField(default=False)
    
    # Success Enablers
    needs_written_instructions = models.BooleanField(default=False)
    prefers_async_communication = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Workplace Passport"