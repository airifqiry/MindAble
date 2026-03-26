from django.contrib import admin
from .models import Company, Job, UserJobInteraction

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_verified_inclusive', 'website')
    search_fields = ('name',)

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'job_type', 'location', 'is_translated')
    list_filter = ('job_type', 'is_translated', 'company')
    search_fields = ('title', 'company__name')

@admin.register(UserJobInteraction)
class UserJobInteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'status', 'created_at')