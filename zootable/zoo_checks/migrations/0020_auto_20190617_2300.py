# Generated by Django 2.2.2 on 2019-06-18 03:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zoo_checks', '0019_auto_20190616_0012'),
    ]

    operations = [
        migrations.AlterField(
            model_name='animalcount',
            name='condition',
            field=models.CharField(choices=[('BA', 'BAR'), ('SE', 'Seen'), ('NA', 'Attn'), ('', 'Not Seen')], default='', max_length=2, null=True),
        ),
    ]