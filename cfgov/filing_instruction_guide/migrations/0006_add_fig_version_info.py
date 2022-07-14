# Generated by Django 3.2.13 on 2022-07-12 20:56

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filing_instruction_guide', '0005_improve_fig_block_names_and_help_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='figcontentpage',
            name='effective_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='figcontentpage',
            name='effective_start_date',
            field=models.DateField(blank=True, default=datetime.date.today, null=True),
        ),
        migrations.AddField(
            model_name='figcontentpage',
            name='version_status',
            field=models.CharField(choices=[('current', 'Current'), ('old', 'Out-of-date'), ('archived', 'Archived')], default='current', max_length=20),
        ),
    ]
