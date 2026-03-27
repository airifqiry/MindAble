

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkplaceProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resume_pdf', models.FileField(blank=True, null=True, upload_to='resumes/')),
                ('experience_summary', models.TextField(blank=True)),
                ('skills', models.TextField(blank=True)),
                ('success_enablers', models.JSONField(blank=True, default=dict)),
                ('dealbreakers', models.JSONField(blank=True, default=list)),
                ('mental_disability', models.TextField(blank=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.DeleteModel(
            name='WorkplacePassport',
        ),
    ]
