

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_job_needs_embedding_job_skills_embedding'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='needs_embedding',
        ),
        migrations.RemoveField(
            model_name='job',
            name='skills_embedding',
        ),
    ]
