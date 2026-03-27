

import django.contrib.postgres.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_workplaceprofile_delete_workplacepassport'),
    ]

    operations = [
        migrations.CreateModel(
            name='RejectedJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_id', models.CharField(max_length=100)),
                ('skills_embedding', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=384)),
                ('needs_embedding', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=384)),
                ('reason', models.TextField(blank=True, null=True)),
                ('rejected_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rejected_jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'job_id')},
            },
        ),
    ]
