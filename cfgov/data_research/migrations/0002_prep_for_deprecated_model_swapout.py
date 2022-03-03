# Generated by Django 3.2.5 on 2021-07-21 04:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_research', '0001_squashed_0013_auto_20200811_1143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conferenceregistration',
            name='details',
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name='metroarea',
            name='counties',
            field=models.JSONField(blank=True, help_text='FIPS list of counties in the MSA'),
        ),
        migrations.AlterField(
            model_name='metroarea',
            name='states',
            field=models.JSONField(blank=True, help_text='FIPS list of states touched by MSA'),
        ),
        migrations.AlterField(
            model_name='mortgagemetadata',
            name='json_value',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='state',
            name='counties',
            field=models.JSONField(blank=True, help_text='FIPS list of counties in the state'),
        ),
        migrations.AlterField(
            model_name='state',
            name='msas',
            field=models.JSONField(blank=True, help_text='FIPS list of MSAs in the state'),
        ),
        migrations.AlterField(
            model_name='state',
            name='non_msa_counties',
            field=models.JSONField(blank=True, help_text='FIPS list of counties in the state that are not in an MSA'),
        ),
    ]
