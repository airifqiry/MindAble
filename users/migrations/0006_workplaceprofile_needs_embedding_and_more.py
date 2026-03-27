

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_remove_workplaceprofile_needs_embedding_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workplaceprofile',
            name='needs_embedding',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), blank=True, null=True, size=384),
        ),
        migrations.AddField(
            model_name='workplaceprofile',
            name='skills_embedding',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), blank=True, null=True, size=384),
        ),
    ]
