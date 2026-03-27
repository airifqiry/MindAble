

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_workplaceprofile_needs_embedding_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workplaceprofile',
            name='needs_embedding',
        ),
        migrations.RemoveField(
            model_name='workplaceprofile',
            name='skills_embedding',
        ),
    ]
