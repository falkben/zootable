# Generated by Django 3.0.11 on 2020-11-25 20:18

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('zoo_checks', '0012_auto_20190609_0013_squashed_0039_auto_20200724_2335'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnimalPhoto',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('image', models.ImageField(upload_to='')),
                ('animal', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='photo', to='zoo_checks.Animal')),
            ],
        ),
    ]
