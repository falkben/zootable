# Generated by Django 2.2.1 on 2019-06-06 04:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zoo_checks', '0005_auto_20190606_0410'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='animalcount',
            options={'ordering': ['datecounted']},
        ),
        migrations.AlterModelOptions(
            name='speciescount',
            options={'ordering': ['datecounted']},
        ),
        migrations.RemoveField(
            model_name='animalcount',
            name='datetimecounted',
        ),
        migrations.RemoveField(
            model_name='speciescount',
            name='datetimecounted',
        ),
        migrations.AddField(
            model_name='animalcount',
            name='datecounted',
            field=models.DateField(auto_now=True),
        ),
        migrations.AddField(
            model_name='speciescount',
            name='datecounted',
            field=models.DateField(auto_now=True),
        ),
    ]
