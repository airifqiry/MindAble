from django.contrib import admin
from .models import WorkplaceProfile

@admin.register(WorkplaceProfile)
class WorkplaceProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'experience_summary')
    search_fields = ('user__username', 'skills')