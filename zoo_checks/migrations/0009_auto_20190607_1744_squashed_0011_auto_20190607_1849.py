# Generated by Django 2.2.2 on 2019-06-07 20:44

from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [('zoo_checks', '0009_auto_20190607_1744'), ('zoo_checks', '0010_animal_sex'), ('zoo_checks', '0011_auto_20190607_1849')]

    dependencies = [
        ('zoo_checks', '0008_auto_20190607_1318_squashed_0016_auto_20190607_1617'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exhibit',
            name='name',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name='animal',
            name='sex',
            field=models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')], default='U', max_length=1),
        ),
    ]
